"""Validated, repeatable import of the pinned GOODS-S teaching dataset.

No deletes, collection replacement, image uploads, or pair materialization.
"""

import json
from math import isclose, isfinite
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from .catalog import validate_galaxy_id
from .data import load_sample, sha256
from .imaging import project_markers


ROOT = Path(__file__).resolve().parents[1]
MAP_ID = "goods-s"
EXPECTED_COUNT = 43


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare_import(root=ROOT):
    """Validate every source and all image/WCS joins before any database writes."""
    sample, galaxies = load_sample(root / "data/sample.json")
    measurements = json.loads((root / "results/measurements.json").read_text(encoding="utf-8"))
    positions = json.loads((root / "results/markers.json").read_text(encoding="utf-8"))
    dataset = sample["dataset"]
    require(dataset == measurements["dataset"], "Source and export dataset metadata differ.")
    require(measurements["cosmology"]["name"] == "Planck18", "Unexpected cosmology.")
    require(len(galaxies) == EXPECTED_COUNT, "Expected exactly 43 GOODS-S galaxies.")
    ids = {g.galaxy_id for g in galaxies}
    exports = {g["galaxy_id"]: g for g in measurements["galaxies"]}
    markers = {m["galaxy_id"]: m for m in positions["markers"]}
    require(len(exports) == len(measurements["galaxies"]) == EXPECTED_COUNT and set(exports) == ids,
            "Galaxy export IDs differ or are duplicated.")
    require(len(markers) == len(positions["markers"]) == EXPECTED_COUNT and set(markers) == ids,
            "Marker IDs differ or are duplicated.")
    require(positions["shape_yx"] == dataset["image_geometry"]["shape_yx"] == [2000, 2000],
            "Unexpected image dimensions.")
    require(positions["pixel_origin"] == 0 and positions["display_origin"] == "lower",
            "Unsupported pixel convention.")
    for g in galaxies:
        validate_galaxy_id(g.galaxy_id)
        require(g.redshift_quality == "A" and g.has_coordinates and g.has_reliable_redshift,
                "Expected quality-A galaxies with coordinates and redshifts.")
        require(all(exports[g.galaxy_id].get(k) == v for k, v in g.metadata().items()),
                "Source galaxy metadata differs from its export.")
        m = markers[g.galaxy_id]
        require(m["inside_image"] is True and all(
            isinstance(m[k], (int, float)) and not isinstance(m[k], bool)
            and isfinite(m[k]) and -0.5 <= m[k] < 1999.5 for k in ("x", "y")
        ), "Invalid marker coordinates.")
    image = root / "data" / dataset["image_file"]
    require(sha256(image) == dataset["cutout_sha256"], "Reference FITS checksum changed.")
    with fits.open(image) as hdul:
        require(list(hdul[0].data.shape) == positions["shape_yx"], "FITS dimensions changed.")
        wcs = WCS(hdul[0].header, fix=False).celestial
        projected = project_markers(galaxies, wcs, hdul[0].data.shape)
        wcs_header = wcs.to_header(relax=True).tostring(sep="\n", endcard=True, padding=False)
    for m in projected:
        require(all(isclose(m[k], markers[m["galaxy_id"]][k], rel_tol=0, abs_tol=1e-6)
                    for k in ("x", "y")), "Export marker differs from FITS WCS.")
    assets = {}
    for mode, stem in (("color", "goods_s_color"), ("grayscale", "goods_s_f200w")):
        with Image.open(root / "results" / f"{stem}.png") as png:
            require(png.size == (2000, 2000), "Static PNG dimensions changed.")
        assets[mode] = []
        for width in (640, 1280, 2000):
            asset = f"{stem}-{width}.webp"
            with Image.open(root / "frontend/src/assets" / asset) as webp:
                require(webp.size == (width, width), "Static WebP dimensions changed.")
            assets[mode].append({"asset": asset, "width": width})
    provenance = {k: v for k, v in dataset.items() if k.startswith("catalog_") or k in {
        "apparent_size", "id_convention", "coordinate_columns", "redshift_column",
        "redshift_quality_column", "redshift_uncertainty_column", "redshift_uncertainty_note",
        "quality_documentation_url", "release_note", "license",
    }}
    galaxy_docs = [{**g.metadata(), "catalog_provenance": provenance} for g in galaxies]
    marker_docs = [{"map_id": MAP_ID, **m} for m in positions["markers"]]
    map_doc = {
        **{k: v for k, v in measurements.items() if k not in {"galaxies", "pairs"}},
        "map_id": MAP_ID, "title": "GOODS-S", "galaxy_count": EXPECTED_COUNT,
        "galaxy_ids": sorted(ids),
        **{k: v for k, v in positions.items() if k != "markers"},
        "image_assets": assets,
        "source_images": {"color": "results/goods_s_color.png", "grayscale": "results/goods_s_f200w.png"},
        "color_provenance_reference": "results/goods_s_color.md",
        "wcs_header": wcs_header,
        "coordinate_frame": "ICRS", "coordinate_unit": "deg",
        "browser_coordinates": {"x": "x", "y": "height - 1 - y", "viewbox_origin_xy": [-0.5, -0.5]},
    }
    prepared = {"map": map_doc, "galaxies": galaxy_docs, "markers": marker_docs}
    json.dumps(prepared, allow_nan=False)
    return prepared


def verify_import(database, prepared):
    """Compare every imported field, including nulls and exact marker doubles."""
    expected_ids = set(prepared["map"]["galaxy_ids"])
    actual_markers = list(database.map_markers.find({"map_id": MAP_ID}, {"_id": 0}))
    require(len(actual_markers) == EXPECTED_COUNT
            and {m["galaxy_id"] for m in actual_markers} == expected_ids,
            "GOODS-S must contain exactly 43 expected markers.")
    for collection, documents, keys in (
        (database.maps, [prepared["map"]], ("map_id",)),
        (database.galaxies, prepared["galaxies"], ("galaxy_id",)),
        (database.map_markers, prepared["markers"], ("map_id", "galaxy_id")),
    ):
        for document in documents:
            query = {k: document[k] for k in keys}
            require(collection.count_documents(query) == 1, "Missing or duplicated imported record.")
            actual = collection.find_one(query, {"_id": 0})
            require(all(actual.get(k) == v for k, v in document.items()), "Imported metadata differs from source.")
    return {"maps": 1, "galaxies": EXPECTED_COUNT, "map_markers": EXPECTED_COUNT}


def import_data(database, prepared):
    """Upsert only these stable IDs; retain other documents and extra fields."""
    expected = set(prepared["map"]["galaxy_ids"])
    existing = list(database.map_markers.find({"map_id": MAP_ID}, {"galaxy_id": 1}))
    require(all(m.get("galaxy_id") in expected for m in existing),
            "GOODS-S contains unexpected markers; refusing to remove unrelated records.")
    database.galaxies.create_index("galaxy_id", unique=True, sparse=True, name="unique_galaxy_id")
    database.maps.create_index("map_id", unique=True, sparse=True, name="unique_map_id")
    database.map_markers.create_index([("map_id", 1), ("galaxy_id", 1)], unique=True,
        partialFilterExpression={"map_id": {"$type": "string"}, "galaxy_id": {"$type": "string"}},
        name="unique_map_galaxy")
    counts = {}
    # Publish metadata last, after all referenced records have been written.
    for name, documents, keys in (
        ("galaxies", prepared["galaxies"], ("galaxy_id",)),
        ("map_markers", prepared["markers"], ("map_id", "galaxy_id")),
        ("maps", [prepared["map"]], ("map_id",)),
    ):
        inserted = modified = 0
        for document in documents:
            result = database[name].update_one({k: document[k] for k in keys}, {"$set": document}, upsert=True)
            inserted += result.upserted_id is not None
            modified += result.modified_count
        counts[name] = {"processed": len(documents), "inserted": inserted, "modified": modified}
    return {"imported": counts, "verified": verify_import(database, prepared)}
