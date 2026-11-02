import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from astropy.table import MaskedColumn, Table
from astropy.wcs import WCS
from PIL import Image
import pytest

from starmap import Galaxy
from starmap.cli import main
from starmap.data import load_catalog, load_sample
from starmap.imaging import export_clean_image, project_markers
from starmap.calculations import comoving_distance_ly
from starmap.output import build_results
from starmap.selection import select_pairs
from starmap.verify import verify

ROOT = Path(__file__).resolve().parents[1]


def test_projection_retains_crop_and_scale():
    parent = WCS(naxis=2)
    parent.wcs.crpix = [100, 100]
    parent.wcs.cdelt = [-0.03 / 3600, 0.03 / 3600]
    parent.wcs.crval = [53.16, -27.77]
    parent.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    sky = parent.pixel_to_world(120, 130)
    g = Galaxy("known", float(sky.ra.deg), float(sky.dec.deg), 1.0, "A")
    cropped = parent.slice((slice(80, 180), slice(70, 170)))
    marker = project_markers([g], cropped, (100, 100))[0]
    assert marker["x"] == pytest.approx(50, abs=1e-6)
    assert marker["y"] == pytest.approx(50, abs=1e-6)
    assert marker["inside_image"]


def test_unknown_and_duplicate_ids_are_rejected():
    g = Galaxy("known", 0, 0, 1, "A")
    with pytest.raises(ValueError, match="Unknown galaxy ID"):
        select_pairs([g], [["known", "missing"]])
    with pytest.raises(ValueError, match="Duplicate"):
        select_pairs([g, g], [["known", "known"]])
    with pytest.raises(ValueError, match="exactly two"):
        select_pairs([g], [["known"]])


def test_catalog_rejects_masked_invalid_and_unreliable_records(tmp_path):
    table = Table({
        "NIRSpec_ID": list(range(8)), "TIER": ["goods-s-deephst"] * 8,
        "NIRCam_ID": [10, 11, 12, 13, 14, -9999, 16, 17],
        "RA_NIRCam": [53.16, 53.16, 53.16, 53.16, 53.16, 53.16, 53.16, 53.16],
        "Dec_NIRCam": [-27.77, -27.77, -91, -27.77, -27.77, -27.77, -27.77, -27.77],
        "z_Spec": [1, 1, 1, -1, 1, 1, 1, 1],
        "z_Spec_flag": ["A", "D", "A", "A", "A", "A", "A", "A"],
        "DR_flag": [False, False, False, False, True, False, False, False],
    })
    table.replace_column("NIRCam_ID", MaskedColumn(table["NIRCam_ID"], mask=[False] * 7 + [True]))
    table.replace_column("RA_NIRCam", MaskedColumn(table["RA_NIRCam"], mask=[False] * 6 + [True, False]))
    path = tmp_path / "catalog.fits"
    table.write(path)
    galaxies = load_catalog(path)
    assert [g.nirspec_id for g in galaxies] == [0]


def test_offline_cli_outputs_three_pairs(tmp_path, capsys):
    output = tmp_path / "result.json"
    main(["--sample", str(ROOT / "data/sample.json"), "--pairs", str(ROOT / "data/pairs.json"),
          "--output", str(output)])
    result = json.loads(output.read_text())
    assert len(result["pairs"]) == 3
    assert len(result["galaxies"]) == 15
    assert result["cosmology"]["name"] == "Planck18"
    assert all(p["status"] == "available" for p in result["pairs"])
    assert all(g["redshift_uncertainty"] is None for g in result["galaxies"])
    _, source = load_sample(ROOT / "data/sample.json")
    for exported, galaxy in zip(result["galaxies"], source):
        assert exported["distance_from_us"] == {
            "value": comoving_distance_ly(galaxy), "unit": "ly", "convention": "comoving",
        }
    assert "comoving" in capsys.readouterr().out


def test_per_galaxy_export_keeps_unknown_distance_explicit():
    document, galaxies = load_sample(ROOT / "data/sample.json")
    unknown = replace(galaxies[0], redshift=None)
    exported = build_results(document, [unknown], [])["galaxies"][0]
    assert exported["distance_from_us"] == {"value": None, "unit": "ly", "convention": "comoving"}
    assert exported["distance_status"] == "unknown"


def test_clean_png_preserves_dimensions_and_flips_pixel_rows(tmp_path):
    # A non-square, asymmetric array makes resizing or a missed Y flip observable.
    pixels = np.array([[0., 1., 2.], [3., 4., 5.]])
    output = tmp_path / "clean.png"
    export_clean_image(pixels, output)
    with Image.open(output) as image:
        assert image.size == (3, 2)
        rgba = np.asarray(image)
    assert rgba[0, 0, 0] > rgba[1, 0, 0]
    assert rgba[0, 2, 0] > rgba[0, 0, 0]


def test_cli_pair_override_and_invalid_id(tmp_path):
    _, galaxies = load_sample(ROOT / "data/sample.json")
    g = galaxies[0]
    output = tmp_path / "result.json"
    args = ["--sample", str(ROOT / "data/sample.json"), "--output", str(output)]
    main(args + ["--pair", g.galaxy_id, g.galaxy_id])
    assert json.loads(output.read_text())["pairs"][0]["estimated_3d_separation"]["value"] == 0
    with pytest.raises(SystemExit) as exc:
        main(args + ["--pair", g.galaxy_id, "missing"])
    assert exc.value.code == 2


def test_pinned_dataset_geometry_and_calculations():
    result = verify(ROOT / "data/sample.json", ROOT / "data/pairs.json")
    assert result["status"] == "passed"
    assert result["markers_inside_image"] == 15
    assert len(result["cross_checks"]) == 3
