"""One-time, cached data preparation. No network access during calculations."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

from .data import (CATALOG_SHA256, CATALOG_URL, IMAGE_URL, README_URL, download_cached,
                   load_catalog, sha256, write_json)
from .models import QUALITY_MEANINGS
from .sizes import SIZE_URL, SIZE_DOCUMENTATION_URL, SIZE_MEASUREMENT, load_sizes, attach_sizes

# Fixed sky region; selection is independent of computed pair distances.
CENTER_RA_DEG = 53.160622050813075
CENTER_DEC_DEG = -27.771611286298103
CUTOUT_PIXELS = 2000

def select_cutout_galaxies(galaxies, wcs, shape, preferred_ids=()):
    """All eligible sources in this image; deduplicate repeated spectroscopy."""
    preferred = set(preferred_ids)
    candidates = sorted(galaxies, key=lambda g: (g.galaxy_id not in preferred, g.galaxy_id))
    unique = {}
    for galaxy in candidates:
        if galaxy.redshift_quality != "A" or not galaxy.has_coordinates or not galaxy.has_reliable_redshift:
            continue
        x, y = wcs.world_to_pixel_values(galaxy.ra_deg, galaxy.dec_deg)
        if -0.5 <= x < shape[1] - 0.5 and -0.5 <= y < shape[0] - 0.5:
            unique.setdefault(galaxy.nircam_id, galaxy)
    return sorted(unique.values(), key=lambda g: g.galaxy_id)


def fetch_cutout(destination: Path, source_header: Path) -> dict:
    """Read just a SCI section via HTTP ranges; cache a native-resolution FITS.

    Never use hdul['SCI'].data here: that would fetch the entire mosaic.
    Readahead fetches contiguous row spans; transfer exceeds the cutout size
    but is still far below the full 11 GB, four-extension source product.
    """
    with fits.open(IMAGE_URL, use_fsspec=True, lazy_load_hdus=True,
                   fsspec_kwargs={"block_size": 8 * 1024 * 1024,
                                  "cache_type": "readahead"}) as hdul:
        sci = hdul["SCI"]
        header = sci.header.copy()
        wcs = WCS(header, fix=False).celestial
        center = SkyCoord(CENTER_RA_DEG, CENTER_DEC_DEG, unit="deg")
        cx, cy = wcs.world_to_pixel(center)
        x0, y0 = int(round(float(cx))) - CUTOUT_PIXELS // 2, int(round(float(cy))) - CUTOUT_PIXELS // 2
        x1, y1 = x0 + CUTOUT_PIXELS, y0 + CUTOUT_PIXELS
        if not (0 <= x0 < x1 <= header["NAXIS1"] and 0 <= y0 < y1 <= header["NAXIS2"]):
            raise ValueError("Cutout exceeds mosaic bounds")
        print(f"Fetching SCI pixels x=[{x0},{x1}), y=[{y0},{y1}) ...", flush=True)
        pixels = sci.section[y0:y1, x0:x1].copy()
        cutout_wcs = wcs.slice((slice(y0, y1), slice(x0, x1)))
        cutout_header = cutout_wcs.to_header()
        for key in ("BUNIT", "FILTER", "TELESCOP", "INSTRUME"):
            if key in header:
                cutout_header[key] = header[key]
            elif key in hdul[0].header:
                cutout_header[key] = hdul[0].header[key]
        cutout_header["HISTORY"] = "Native SCI crop; no resizing or reprojection."
        fits.PrimaryHDU(pixels, cutout_header).writeto(destination, overwrite=True)
        source_header.write_text(header.tostring(sep="\n", endcard=True, padding=False), encoding="ascii")
    return {"origin_in_parent_pixels_zero_based": [x0, y0],
            "shape_yx": [CUTOUT_PIXELS, CUTOUT_PIXELS],
            "parent_shape_yx": [header["NAXIS2"], header["NAXIS1"]],
            "source_extension": "SCI", "resized": False,
            "pixel_convention": "zero-based pixel centers; x right, y up in origin=lower plots"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args(argv)
    root = args.data_dir
    cache = root / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    catalog = download_cached(CATALOG_URL, cache / "catalog.fits")
    if sha256(catalog) != CATALOG_SHA256:
        raise ValueError("Catalog checksum differs from the pinned DR3 product; inspect before updating the sample")
    download_cached(README_URL, cache / "source_readme.txt")
    image = root / "goods_s_f200w_cutout.fits"
    geometry_file = cache / "cutout_geometry.json"
    if image.exists() and geometry_file.exists():
        geometry = json.loads(geometry_file.read_text(encoding="utf-8"))
    elif image.exists() and (root / "sample.json").exists() and (root / "parent_sci_header.txt").exists():
        pinned = json.loads((root / "sample.json").read_text(encoding="utf-8"))["dataset"]
        if sha256(image) != pinned["cutout_sha256"]:
            raise ValueError("Bundled image checksum mismatch; inspect before rebuilding")
        geometry = pinned["image_geometry"]
        write_json(geometry_file, geometry)
    else:
        geometry = fetch_cutout(image, root / "parent_sci_header.txt")
        write_json(geometry_file, geometry)
    old_document = json.loads((root / "sample.json").read_text(encoding="utf-8")) if (root / "sample.json").exists() else {"galaxies": []}
    preferred_ids = [g["galaxy_id"] for g in old_document["galaxies"]]
    with fits.open(image) as hdul:
        galaxies = select_cutout_galaxies(load_catalog(catalog),
            WCS(hdul[0].header, fix=False).celestial, hdul[0].data.shape, preferred_ids)
    size_cache = cache / "photometry_sizes.fits"
    galaxies = attach_sizes(galaxies, load_sizes(size_cache))
    dataset = {
        "field": "GOODS-S", "catalog_release": "JADES DR3", "catalog_version": "v1.1",
        "catalog_url": CATALOG_URL, "catalog_hdu": 1, "catalog_sha256": sha256(catalog),
        "image_release": "JADES DR2", "image_version": "v2.0",
        "image_url": IMAGE_URL, "instrument": "JWST/NIRCam", "filter": "F200W",
        "image_file": image.name, "cutout_sha256": sha256(image),
        "image_geometry": geometry,
        "image_center_icrs_deg": [CENTER_RA_DEG, CENTER_DEC_DEG],
        "coordinate_columns": ["RA_NIRCam", "Dec_NIRCam"],
        "redshift_column": "z_Spec", "redshift_quality_column": "z_Spec_flag",
        "redshift_uncertainty_column": None,
        "redshift_uncertainty_note": "No published z_Spec uncertainty column in this table; line-flux errors are not redshift errors.",
        "selection": "All NIRCam-matched flag-A sources inside the existing cutout, z>0, DR_flag=False, deduplicated by NIRCam_ID across all tiers. Existing canonical IDs retained; otherwise lexicographic TIER:NIRSpec_ID tie-break.",
        "apparent_size": {"catalog_url": SIZE_URL, "release": "JADES DR2 v2.0", "hdu": "SIZE",
            "column": "F200W_RHALF", "unit": "arcsec", "meaning": SIZE_MEASUREMENT,
            "documentation_url": SIZE_DOCUMENTATION_URL, "documentation_page": 5,
            "match_radius_arcsec": 0.2, "cached_table_sha256": sha256(size_cache),
            "match_note": "ID plus sky match within 0.2 arcsec; nearest sky match if IDs changed through re-segmentation. Unavailable sizes remain null."},
        "id_convention": "TIER:NIRSpec_ID; NIRCam_ID is retained separately, not used interchangeably.",
        "quality_flag_meanings": QUALITY_MEANINGS,
        "quality_documentation_url": README_URL,
        "release_note": "Fixed archival teaching dataset; DR4 supersedes most DR3 spectroscopy. No claim of using the latest redshifts.",
        "references": ["https://archive.stsci.edu/hlsp/jades", README_URL,
                       "https://doi.org/10.17909/8tdj-8n28",
                       "https://arxiv.org/abs/2404.06531",
                       "https://arxiv.org/abs/2310.12340"],
        "license": "CC BY 4.0 (JADES HLSP products)",
    }
    with fits.open(image) as hdul:
        wcs = WCS(hdul[0].header, fix=False).celestial
        for g in galaxies:
            x, y = wcs.world_to_pixel(SkyCoord(g.ra_deg, g.dec_deg, unit="deg"))
            if not (0 <= x < CUTOUT_PIXELS and 0 <= y < CUTOUT_PIXELS):
                raise ValueError(f"{g.galaxy_id} falls outside cutout")
    write_json(root / "sample.json", {"dataset": dataset, "galaxies": [asdict(g) for g in galaxies]})
    print(f"Saved {len(galaxies)} galaxies to {root / 'sample.json'}")
    for g in galaxies:
        print(f"  {g.galaxy_id}  NIRCam={g.nircam_id}  z={g.redshift:.8f}  quality=A")


if __name__ == "__main__":
    main()
