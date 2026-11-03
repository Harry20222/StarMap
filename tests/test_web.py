"""Check the deployed adapter against the actual exports without an HTTP server."""

import json

import pytest
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

from app import RESULTS, app


def request(path, method="GET"):
    environ = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD=method, QUERY_STRING="")
    response = {}

    def start_response(status, headers, exc_info=None):
        response.update(status=status, headers=dict(headers))

    iterator = validator(app)(environ, start_response)
    try:
        response["body"] = b"".join(iterator)
    finally:
        iterator.close()
    return response


@pytest.mark.parametrize("name", ["markers.json", "measurements.json"])
def test_exports_match_files_and_head_has_no_body(name):
    response = request(f"/api/{name}")
    expected = (RESULTS / name).read_bytes()
    assert response["status"] == "200 OK"
    assert response["body"] == expected
    assert response["headers"]["Content-Type"].startswith("application/json")
    assert response["headers"]["Content-Length"] == str(len(expected))
    head = request(f"/api/{name}", "HEAD")
    assert head["status"] == "200 OK"
    assert head["headers"] == response["headers"]
    assert head["body"] == b""


def test_prefix_health_and_method_handling():
    assert json.loads(request("/api/health")["body"]) == {"status": "ok"}
    assert json.loads(request("/api")["body"])["service"] == "app"
    for path in ("/health", "/measurements.json", "/api/../pyproject.toml", "/api/unknown"):
        assert request(path)["status"] == "404 Not Found"
    response = request("/api/measurements.json", "POST")
    assert response["status"] == "405 Method Not Allowed"
    assert response["headers"]["Allow"] == "GET, HEAD"
    assert response["headers"]["Cache-Control"] == "no-store"
