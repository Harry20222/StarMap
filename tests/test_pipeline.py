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
from starmap.prepare import select_cutout_galaxies
from starmap.sizes import attach_sizes, SIZE_MEASUREMENT

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


def test_offline_cli_exports_all_pairs_and_prints_examples(tmp_path, capsys):
    output = tmp_path / "result.json"
    main(["--sample", str(ROOT / "data/sample.json"), "--pairs", str(ROOT / "data/pairs.json"),
          "--output", str(output)])
    result = json.loads(output.read_text())
    count = len(result["galaxies"])
    assert count == 43
    assert len(result["pairs"]) == count * (count - 1) // 2
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
    assert result["markers_inside_image"] == 43
    assert len(result["cross_checks"]) == 3


def test_initial_fifteen_have_all_105_unique_pairs():
    document, galaxies = load_sample(ROOT / "data/prototype1_sample.json")
    result = build_results(document, galaxies)
    assert len(galaxies) == 15 and len(result["pairs"]) == 105
    keys = {frozenset((p["galaxy_a_id"], p["galaxy_b_id"])) for p in result["pairs"]}
    assert len(keys) == 105 and all(len(key) == 2 for key in keys)


def test_expansion_contains_every_eligible_unique_source_in_cutout():
    if not (ROOT / "data/cache/catalog.fits").exists():
        pytest.skip("Optional original catalog cache is not present")
    document, galaxies = load_sample(ROOT / "data/sample.json")
    original, old_galaxies = load_sample(ROOT / "data/prototype1_sample.json")
    from astropy.io import fits
    with fits.open(ROOT / "data/goods_s_f200w_cutout.fits") as h:
        wcs = WCS(h[0].header, fix=False).celestial
        expected = select_cutout_galaxies(load_catalog(ROOT / "data/cache/catalog.fits"), wcs, h[0].data.shape,
            [g.galaxy_id for g in old_galaxies])
    assert len(galaxies) == 43
    assert {g.galaxy_id for g in galaxies} == {g.galaxy_id for g in expected}
    assert len({g.nircam_id for g in galaxies}) == len(galaxies)
    assert {g.galaxy_id for g in old_galaxies} <= {g.galaxy_id for g in galaxies}
    assert all(g.redshift_quality == "A" for g in galaxies)
    assert all(g.apparent_size_arcsec > 0 and g.apparent_size_measurement == SIZE_MEASUREMENT for g in galaxies)
    assert all(g.size_match_separation_arcsec <= 0.2 for g in galaxies)
    assert document["dataset"]["apparent_size"]["unit"] == "arcsec"
    assert document["dataset"]["cutout_sha256"] == original["dataset"]["cutout_sha256"]


def test_size_matching_checks_sky_position_and_keeps_missing_size_unknown():
    table = Table({"ID": [10, 20], "RA": [10., 53.16], "DEC": [0., -27.77], "F200W_RHALF": [0.1, 0.4]})
    g = Galaxy("match", 53.16, -27.77, 2., "A", nircam_id=10)
    matched = attach_sizes([g], table)[0]
    assert matched.size_catalog_id == 20  # Same input ID was at the wrong sky position.
    assert matched.apparent_size_arcsec == 0.4
    assert matched.apparent_size_measurement == SIZE_MEASUREMENT
    absent = attach_sizes([replace(g, ra_deg=100.)], table)[0]
    assert absent.apparent_size_arcsec is None and absent.size_catalog_id is None
    table['F200W_RHALF'][1] = -1
    assert attach_sizes([g], table)[0].apparent_size_arcsec is None
