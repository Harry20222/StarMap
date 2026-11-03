"""Published DR2 F200W circularized half-light radii, matched on the sky."""

from dataclasses import replace
from pathlib import Path

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table

SIZE_URL = (
    "https://archive.stsci.edu/hlsps/jades/dr2/goods-s/catalogs/"
    "hlsp_jades_jwst_nircam_goods-s-deep_photometry_v2.0_catalog.fits"
)
SIZE_DOCUMENTATION_URL = (
    "https://archive.stsci.edu/hlsps/jades/"
    "hlsp_jades_jwst_nircam_goods-s-deep_photometry_v2.0_catalog-ext-readme.pdf"
)
SIZE_MEASUREMENT = "JADES DR2 SIZE.F200W_RHALF (circularized half-light radius)"


def load_sizes(cache: Path):
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        with fits.open(SIZE_URL, use_fsspec=True,
                       fsspec_kwargs={"block_size": 1024 * 1024, "cache_type": "readahead"}) as hdul:
            table = Table(hdul["SIZE"].data)[["ID", "RA", "DEC", "NPIX_DET", "A", "F200W_RHALF"]]
            table.write(cache)
    return Table.read(cache)


def attach_sizes(galaxies, table):
    coordinates = SkyCoord(np.asarray(table["RA"]), np.asarray(table["DEC"]), unit="deg")
    by_id = {int(row["ID"]): i for i, row in enumerate(table)}
    result = []
    for galaxy in galaxies:
        sky = SkyCoord(galaxy.ra_deg, galaxy.dec_deg, unit="deg")
        index = by_id.get(galaxy.nircam_id)
        separation = (float(sky.separation(coordinates[index]).arcsec)
                      if index is not None else float("inf"))
        if separation > 0.2:
            match, distance, _ = sky.match_to_catalog_sky(coordinates)
            index = int(np.asarray(match).item())
            separation = float(np.asarray(distance.arcsec).item())
        # Re-segmentation can change IDs between releases. Require a spatial
        # match even when IDs agree, and retain the photometric ID separately.
        if separation <= 0.2:
            row = table[index]
            value = float(row["F200W_RHALF"])
            valid_size = np.isfinite(value) and value > 0
            galaxy = replace(galaxy,
                apparent_size_arcsec=value if valid_size else None,
                apparent_size_measurement=SIZE_MEASUREMENT if valid_size else None,
                size_catalog_id=int(row["ID"]), size_match_separation_arcsec=separation)
        result.append(galaxy)
    return result
