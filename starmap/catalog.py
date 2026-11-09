"""Read-only catalog access. Only specific validated IDs become query values."""

from dataclasses import fields
import re

from .calculations import comoving_distance_ly, measure_pair
from .models import Galaxy


class CatalogError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def validate_map_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", value):
        raise CatalogError(400, "Invalid map ID.")
    return value


def validate_galaxy_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}:[0-9]{1,20}", value):
        raise CatalogError(400, "Invalid galaxy ID. Use the full catalog ID.")
    return value


def galaxy_model(document):
    return Galaxy(**{f.name: document.get(f.name) for f in fields(Galaxy)})


def public_galaxy(document):
    galaxy = galaxy_model(document)
    return {
        **galaxy.metadata(),
        "catalog_provenance": document.get("catalog_provenance"),
        "distance_from_us": {
            "value": comoving_distance_ly(galaxy), "unit": "ly", "convention": "comoving",
        },
    }


def list_maps(database):
    return {"maps": list(database.maps.find({"map_id": {"$type": "string"}}, {
        "_id": 0, "map_id": 1, "title": 1, "shape_yx": 1, "galaxy_count": 1,
    }).sort("map_id", 1))}


def get_map(database, map_id):
    validate_map_id(map_id)
    # Explicit projection keeps unrelated/private fields out of public responses.
    projection = {key: 1 for key in (
        "map_id", "title", "galaxy_count", "galaxy_ids", "schema_version", "cosmology",
        "distance_convention", "interpretation", "reliable_redshift_flags", "dataset", "image",
        "shape_yx", "display_image", "pixel_origin", "display_origin", "image_assets",
        "source_images", "color_provenance_reference", "wcs_header", "coordinate_frame",
        "coordinate_unit", "browser_coordinates",
    )}
    document = database.maps.find_one({"map_id": map_id}, {"_id": 0, **projection})
    if document is None:
        raise CatalogError(404, "Map not found.")
    return document


def get_map_galaxies(database, map_id):
    metadata = get_map(database, map_id)
    markers = list(database.map_markers.find({"map_id": map_id}, {
        "_id": 0, "map_id": 1, "galaxy_id": 1, "x": 1, "y": 1, "inside_image": 1,
        "roundtrip_residual_arcsec": 1,
    }).sort("galaxy_id", 1))
    ids = [m["galaxy_id"] for m in markers]
    if "galaxy_ids" in metadata and sorted(ids) != sorted(metadata["galaxy_ids"]):
        raise CatalogError(500, "The map's marker catalog is incomplete. Please contact the site owner.")
    documents = {g["galaxy_id"]: g for g in database.galaxies.find({"galaxy_id": {"$in": ids}}, {"_id": 0})}
    if any(gid not in documents for gid in ids):
        raise CatalogError(404, "A galaxy record referenced by this map is missing.")
    return {"map_id": map_id, "galaxies": [public_galaxy(documents[gid]) for gid in ids], "markers": markers}


def compare_galaxies(database, map_id, a, b):
    validate_map_id(map_id)
    validate_galaxy_id(a)
    validate_galaxy_id(b)
    if a == b:
        raise CatalogError(400, "Select two different galaxies.")
    get_map(database, map_id)
    galaxies = []
    for gid in (a, b):
        if database.map_markers.find_one({"map_id": map_id, "galaxy_id": gid}, {"_id": 1}) is None:
            raise CatalogError(404, "A selected galaxy does not belong to this map.")
        record = database.galaxies.find_one({"galaxy_id": gid}, {"_id": 0})
        if record is None:
            raise CatalogError(404, "A selected galaxy record is missing.")
        galaxies.append(galaxy_model(record))
    return {"map_id": map_id, "cosmology": "Planck18", **measure_pair(*galaxies)}
