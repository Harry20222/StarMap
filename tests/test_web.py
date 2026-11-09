"""WSGI API tests run only against a fresh in-memory database."""

import json
from urllib.parse import urlencode, urlsplit
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

import pytest
from pymongo.errors import ServerSelectionTimeoutError

import app as web
from starmap.database import DatabaseConfigurationError
from starmap.migration import ROOT


def request(path, method="GET"):
    environ = {}
    setup_testing_defaults(environ)
    url = urlsplit(path)
    environ.update(PATH_INFO=url.path, REQUEST_METHOD=method, QUERY_STRING=url.query)
    response = {}

    def start_response(status, headers, exc_info=None):
        response.update(status=status, headers=dict(headers))

    iterator = validator(web.app)(environ, start_response)
    try:
        response["body"] = b"".join(iterator)
    finally:
        iterator.close()
    if response["body"]:
        response["json"] = json.loads(response["body"])
    return response


@pytest.fixture(autouse=True)
def use_isolated_database(monkeypatch, database):
    monkeypatch.setattr(web, "get_database", lambda: database)


def pair_url(a, b, map_id="goods-s"):
    return f"/api/maps/{map_id}/compare?{urlencode({'a': a, 'b': b})}"


def test_maps_catalog_metadata_head_and_no_pair_exports(database, prepared):
    listing = request("/api/maps")
    assert listing["status"] == "200 OK"
    assert listing["json"]["maps"][0]["map_id"] == "goods-s"
    assert listing["json"]["maps"][0]["galaxy_count"] == 43
    for path in ("/api/maps", "/api/maps/goods-s", "/api/maps/goods-s/galaxies"):
        result, head = request(path), request(path, "HEAD")
        assert result["status"] == head["status"] == "200 OK"
        assert head["body"] == b"" and head["headers"] == result["headers"]
    metadata = request("/api/maps/goods-s")["json"]
    assert metadata["wcs_header"] == prepared["map"]["wcs_header"]
    assert metadata["pixel_origin"] == 0 and metadata["display_origin"] == "lower"
    catalog = request("/api/maps/goods-s/galaxies")["json"]
    assert len(catalog["galaxies"]) == len(catalog["markers"]) == 43
    assert "pairs" not in catalog and "pairs" not in metadata
    assert catalog["galaxies"][0]["catalog_provenance"]["catalog_version"] == "v1.1"
    assert request("/api/measurements.json")["status"] == "404 Not Found"
    # Extra fields on shared records are never public API fields.
    database.maps.update_one({"map_id": "goods-s"}, {"$set": {"private_note": "secret"}})
    assert "private_note" not in request("/api/maps/goods-s")["json"]


def test_every_api_pair_matches_all_903_exports():
    exported = json.loads((ROOT / "results/measurements.json").read_text())
    assert len(exported["pairs"]) == 903
    for expected in exported["pairs"]:
        response = request(pair_url(expected["galaxy_a_id"], expected["galaxy_b_id"]))
        assert response["status"] == "200 OK"
        actual = response["json"]
        for key in ("angular_separation", "distance_from_us_a", "distance_from_us_b", "estimated_3d_separation"):
            assert actual[key]["value"] == pytest.approx(expected[key]["value"], rel=1e-10, abs=1e-12)
            assert actual[key]["unit"] == expected[key]["unit"]
        assert actual["status"] == expected["status"]
        assert actual["estimated_3d_separation"]["uncertainty"] is None
        assert actual["cosmology"] == "Planck18"
    example = exported["pairs"][0]
    reverse = request(pair_url(example["galaxy_b_id"], example["galaxy_a_id"]))["json"]
    assert reverse["distance_from_us_a"] == example["distance_from_us_b"]


@pytest.mark.parametrize("path,status", [
    ("/health", 404), ("/api/../pyproject.toml", 404), ("/api/missing", 404),
    ("/api/maps/not-a-map", 404), ("/api/maps/$where", 400),
    ("/api/maps/goods-s?query={}", 400),
    ("/api/maps/goods-s/compare", 400),
    ("/api/maps/goods-s/compare?a=invalid&b=test:1", 400),
    ("/api/maps/goods-s/compare?a=test:1&b=test:2&where=1", 400),
    ("/api/maps/goods-s/compare?a=test:1&a=test:2", 400),
    ("/api/maps/goods-s/compare?a=test:1&b=test:1", 400),
    ("/api/maps/goods-s/compare?a=test:1&b=test:2", 404),
    ("/api/maps/goods-s/compare?a[$ne]=1&b=test:2", 400),
])
def test_invalid_requests(path, status):
    response = request(path)
    assert response["status"].startswith(str(status))
    assert isinstance(response["json"]["error"], str)


def test_membership_and_missing_records(database, prepared):
    a, b = [g["galaxy_id"] for g in prepared["galaxies"][:2]]
    database.galaxies.insert_one({"galaxy_id": "other:1", "redshift": 1})
    assert request(pair_url(a, "other:1"))["status"] == "404 Not Found"
    database.galaxies.delete_one({"galaxy_id": b})
    assert request(pair_url(a, b))["status"] == "404 Not Found"
    assert request("/api/maps/goods-s/galaxies")["status"] == "404 Not Found"
    database.map_markers.delete_one({"galaxy_id": b})
    assert request("/api/maps/goods-s/galaxies")["status"] == "500 Internal Server Error"


@pytest.mark.parametrize("change", [{"redshift": None}, {"ra_deg": None}, {"redshift_quality": "D"}])
def test_unavailable_distances_are_null(database, prepared, change):
    a, b = [g["galaxy_id"] for g in prepared["galaxies"][:2]]
    database.galaxies.update_one({"galaxy_id": a}, {"$set": change})
    pair = request(pair_url(a, b))["json"]
    assert pair["status"] == "unknown"
    assert pair["estimated_3d_separation"]["value"] is None
    assert pair["unknown_reasons"]
    if "ra_deg" in change:
        assert pair["angular_separation"]["value"] is None
    else:
        assert pair["angular_separation"]["value"] is not None
        assert pair["distance_from_us_a"]["value"] is None


@pytest.mark.parametrize("error", [ServerSelectionTimeoutError("credential-bearing detail"), DatabaseConfigurationError("private setting")])
def test_database_failures_are_sanitized_and_retryable(monkeypatch, error):
    def fail():
        raise error
    monkeypatch.setattr(web, "get_database", fail)
    for path in ("/api/health", "/api/maps", "/api/maps/goods-s/galaxies"):
        response = request(path)
        assert response["status"] == "503 Service Unavailable"
        assert response["headers"]["Retry-After"] == "5"
        assert "private" not in response["body"].decode() and "credential" not in response["body"].decode()
        assert response["headers"]["Cache-Control"] == "no-store"


def test_prefix_health_empty_catalog_and_method_handling(database):
    assert request("/api/health")["json"] == {"status": "ok"}
    assert request("/api")["json"]["service"] == "app"
    response = request("/api/maps", "POST")
    assert response["status"] == "405 Method Not Allowed"
    assert response["headers"]["Allow"] == "GET, HEAD"
    database.maps.delete_many({})
    assert request("/api/maps")["json"] == {"maps": []}
