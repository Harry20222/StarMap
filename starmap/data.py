"""Cached source downloads, FITS parsing, and portable JSON sample loading."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from astropy.table import Table

from .models import Galaxy

CATALOG_URL = (
    "https://archive.stsci.edu/hlsps/jades/dr3/goods-s/catalogs/"
    "hlsp_jades_jwst_nirspec_goods-s_prism-line-fluxes_v1.1_catalog.fits"
)
IMAGE_URL = (
    "https://archive.stsci.edu/hlsps/jades/dr2/goods-s/images/"
    "hlsp_jades_jwst_nircam_goods-s-deep_f200w_v2.0_drz.fits"
)
README_URL = "https://archive.stsci.edu/hlsps/jades/hlsp_jades_readme.txt"
CATALOG_SHA256 = "7b532b33159b3ceeebe2eadc378c6cfe2d717723e532c5aecdf34a845b6441eb"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def download_cached(url: str, destination: Path) -> Path:
    if destination.is_file():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    try:
        with urlopen(url, timeout=120) as source, partial.open("wb") as target:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                target.write(block)
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)
    return destination


def load_catalog(path: Path) -> list[Galaxy]:
    """Use the catalog's NIRCam-matched positions, never equate the two IDs."""
    table = Table.read(path, hdu=1)
    result = []
    # DR3 has no z_Spec uncertainty column. Line flux errors are not z errors.
    for index, row in enumerate(table):
        if any(np.ma.is_masked(row[k]) for k in (
            "NIRSpec_ID", "TIER", "NIRCam_ID", "z_Spec_flag", "DR_flag",
            "RA_NIRCam", "Dec_NIRCam", "z_Spec",
        )):
            continue
        if (str(row["z_Spec_flag"]).strip() != "A"
                or bool(row["DR_flag"]) or int(row["NIRCam_ID"]) <= 0):
            continue
        ra, dec, z = (float(row[k]) for k in ("RA_NIRCam", "Dec_NIRCam", "z_Spec"))
        if not (np.isfinite([ra, dec, z]).all() and 0 <= ra < 360
                and -90 <= dec <= 90 and z > 0):
            continue
        tier, spec_id = str(row["TIER"]).strip(), int(row["NIRSpec_ID"])
        result.append(Galaxy(
            galaxy_id=f"{tier}:{spec_id}", ra_deg=ra, dec_deg=dec,
            redshift=z, redshift_quality="A", nirspec_id=spec_id,
            tier=tier, nircam_id=int(row["NIRCam_ID"]), catalog_row_index=index,
        ))
    return result


def load_sample(path: Path) -> tuple[dict, list[Galaxy]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    galaxies = [Galaxy(**row) for row in document["galaxies"]]
    ids = [g.galaxy_id for g in galaxies]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate galaxy IDs in sample")
    return document, galaxies
