"""Read-only MongoDB/Astropy WSGI API, also used by Vercel's Python service."""

from http import HTTPStatus
import json
import os
import re
from urllib.parse import parse_qs

from pymongo.errors import PyMongoError

from starmap import catalog
from starmap.database import DatabaseConfigurationError, get_database


def dispatch(path, query):
    if path in {"/api", "/api/"}:
        return {"service": "app", "routes": ["/api/health", "/api/maps", "/api/maps/{map_id}",
                "/api/maps/{map_id}/galaxies", "/api/maps/{map_id}/compare?a={galaxy_id}&b={galaxy_id}"]}
    if path == "/api/health":
        get_database().command("ping")
        return {"status": "ok"}
    if path == "/api/maps":
        if query:
            raise catalog.CatalogError(400, "This endpoint takes no query parameters.")
        return catalog.list_maps(get_database())
    match = re.fullmatch(r"/api/maps/([^/]+)(?:/(galaxies|compare))?", path)
    if not match:
        raise catalog.CatalogError(404, "Route not found.")
    map_id, action = match.groups()
    catalog.validate_map_id(map_id)
    if action == "compare":
        try:
            if len(query) > 512:
                raise ValueError
            params = parse_qs(query, keep_blank_values=True, strict_parsing=True, max_num_fields=2)
            if set(params) != {"a", "b"} or any(len(v) != 1 for v in params.values()):
                raise ValueError
        except ValueError:
            raise catalog.CatalogError(400, "Provide exactly one a and one b galaxy ID.") from None
        a, b = params["a"][0], params["b"][0]
        catalog.validate_galaxy_id(a)
        catalog.validate_galaxy_id(b)
        return catalog.compare_galaxies(get_database(), map_id, a, b)
    if query:
        raise catalog.CatalogError(400, "This endpoint takes no query parameters.")
    database = get_database()
    return (catalog.get_map_galaxies(database, map_id) if action == "galaxies"
            else catalog.get_map(database, map_id))


def app(environ, start_response):
    """Preserve /api: Vercel service rewrites forward the original path."""
    method = environ.get("REQUEST_METHOD", "GET")
    headers = [("Content-Type", "application/json; charset=utf-8")]
    status = 200
    try:
        if method not in {"GET", "HEAD"}:
            headers.append(("Allow", "GET, HEAD"))
            raise catalog.CatalogError(405, "Use GET or HEAD.")
        payload = dispatch(environ.get("PATH_INFO", "/"), environ.get("QUERY_STRING", ""))
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
    except catalog.CatalogError as error:
        status = error.status
        body = json.dumps({"error": str(error)}).encode("utf-8")
    except (PyMongoError, DatabaseConfigurationError):
        status = 503
        body = b'{"error":"The catalog database is unavailable. Please retry shortly."}'
    except (ValueError, TypeError, KeyError):
        # Never serialize driver errors, configuration values, or tracebacks.
        status = 500
        body = b'{"error":"The catalog could not be read. Please contact the site owner."}'
    headers.extend([
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    if status == 503:
        headers.append(("Retry-After", "5"))
    start_response(f"{status} {HTTPStatus(status).phrase}", headers)
    return [body] if method != "HEAD" else []


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    with make_server("127.0.0.1", int(os.environ.get("PORT", "8000")), app) as server:
        server.serve_forever()
