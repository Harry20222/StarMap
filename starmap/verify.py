"""Reproducible numerical and parent/cutout WCS cross-checks."""

import argparse
import json
from math import atan2, cos, radians, sin
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.constants import c
from astropy.cosmology import Planck18
from astropy.io import fits
from astropy.wcs import WCS
from scipy.integrate import simpson

from .calculations import measure_pair
from .data import load_sample, sha256, write_json
from .imaging import project_markers
from .selection import select_pairs


def require(condition, message):
    if not condition:
        raise ValueError(message)


def independent_pair(a, b):
    """Independent of SkyCoord separation and comoving_distance integration.

    Integrates 1/E(z) on a fixed grid using Simpson's rule, then subtracts
    explicit Cartesian position vectors. Uses Planck18's expansion history,
    including its neutrino prescription, to keep the physical model identical.
    """
    def distance(z):
        grid = np.linspace(0, z, 8193)
        integral = simpson(1 / Planck18.efunc(grid), x=grid)
        return float((c / Planck18.H0).to_value(u.lyr) * integral)

    def direction(g):
        ra, dec = radians(g.ra_deg), radians(g.dec_deg)
        return np.array([cos(dec) * cos(ra), cos(dec) * sin(ra), sin(dec)])

    ua, ub = direction(a), direction(b)
    da, db = distance(a.redshift), distance(b.redshift)
    return {
        "angular_separation_deg": float(np.degrees(atan2(np.linalg.norm(np.cross(ua, ub)), np.dot(ua, ub)))),
        "distance_from_us_a_ly": da, "distance_from_us_b_ly": db,
        "estimated_3d_separation_ly": float(np.linalg.norm(da * ua - db * ub)),
    }


def verify(sample_path: Path, pairs_path: Path):
    document, galaxies = load_sample(sample_path)
    dataset = document["dataset"]
    image = sample_path.parent / dataset["image_file"]
    if sha256(image) != dataset["cutout_sha256"]:
        raise ValueError("Image checksum differs from the pinned sample")
    with fits.open(image) as hdul:
        cutout_wcs = WCS(hdul[0].header, fix=False).celestial
        markers = project_markers(galaxies, cutout_wcs, hdul[0].data.shape)
    parent_header = fits.Header.fromtextfile(sample_path.parent / "parent_sci_header.txt")
    # These time/observer keywords are irrelevant to the celestial transform.
    parent_wcs = WCS(parent_header, fix=False).celestial
    x0, y0 = dataset["image_geometry"]["origin_in_parent_pixels_zero_based"]
    offsets = []
    for g, marker in zip(galaxies, markers):
        px, py = parent_wcs.world_to_pixel_values(g.ra_deg, g.dec_deg)
        offsets.append(float(np.hypot(px - x0 - marker["x"], py - y0 - marker["y"])))
    require(all(m["inside_image"] for m in markers), "Marker outside cutout")
    require(max(offsets) < 1e-6, "Cutout WCS disagrees with parent crop")
    require(max(m["roundtrip_residual_arcsec"] for m in markers) < 1e-6, "WCS roundtrip mismatch")
    raw_catalog = sample_path.parent / "cache" / "catalog.fits"
    catalog_check = "not_present (offline sample is still usable)"
    if raw_catalog.exists():
        require(sha256(raw_catalog) == dataset["catalog_sha256"], "Catalog checksum mismatch")
        table = fits.getdata(raw_catalog, 1)
        for g in galaxies:
            row = table[g.catalog_row_index]
            matches = (
                int(row["NIRSpec_ID"]) == g.nirspec_id
                and str(row["TIER"]).strip() == g.tier
                and int(row["NIRCam_ID"]) == g.nircam_id
                and float(row["z_Spec"]) == g.redshift
                and float(row["RA_NIRCam"]) == g.ra_deg
                and float(row["Dec_NIRCam"]) == g.dec_deg
                and str(row["z_Spec_flag"]).strip() == g.redshift_quality == "A"
                and not bool(row["DR_flag"])
            )
            require(matches, f"Source row mismatch for {g.galaxy_id}")
        catalog_check = f"checksum and all {len(galaxies)} source rows match"
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))["pairs"]
    cross_checks = []
    for a, b in select_pairs(galaxies, pairs):
        main = measure_pair(a, b)
        independent = independent_pair(a, b)
        values = {"angular_separation_deg": main["angular_separation"]["value"],
                  "distance_from_us_a_ly": main["distance_from_us_a"]["value"],
                  "distance_from_us_b_ly": main["distance_from_us_b"]["value"],
                  "estimated_3d_separation_ly": main["estimated_3d_separation"]["value"]}
        errors = {k: abs(values[k] - v) / max(abs(v), 1e-30) for k, v in independent.items()}
        require(max(errors.values()) < 1e-8, "Independent calculation mismatch")
        cross_checks.append({"galaxy_a_id": a.galaxy_id, "galaxy_b_id": b.galaxy_id,
                             "independent_measurements": independent,
                             "relative_differences": errors})
    return {
        "status": "passed", "catalog_check": catalog_check,
        "image_sha256_matches": True, "markers_inside_image": len(markers),
        "max_parent_minus_crop_residual_pixels": max(offsets),
        "max_wcs_roundtrip_residual_arcsec": max(m["roundtrip_residual_arcsec"] for m in markers),
        "independent_method": "8192-interval Simpson integration of Planck18 1/E(z), vector angular separation, Cartesian position subtraction",
        "relative_tolerance": 1e-8, "cross_checks": cross_checks,
        "visual_verification": "See results/alignment_review.md and alignment_stamps.png; numerical WCS checks alone do not prove source identification.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("data/sample.json"))
    parser.add_argument("--pairs", type=Path, default=Path("data/pairs.json"))
    parser.add_argument("--output", type=Path, default=Path("results/verification.json"))
    args = parser.parse_args(argv)
    result = verify(args.sample, args.pairs)
    write_json(args.output, result)
    print(f"Verification passed: {result['markers_inside_image']} markers, {len(result['cross_checks'])} independent pair checks.")
    print(f"JSON: {args.output}")


if __name__ == "__main__":
    main()
