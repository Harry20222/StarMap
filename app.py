"""Read-only WSGI adapter for the existing exports, deployed as Vercel's app service.

The React app still bundles these same files at build time. This adapter does
not run the exporter, download observations, or recalculate any measurements.
"""

from functools import lru_cache
import json
import os
from pathlib import Path


RESULTS = Path(__file__).resolve().parent / "results"
EXPORTS = {
    "/api/markers.json": "markers.json",
    "/api/measurements.json": "measurements.json",
}


@lru_cache(maxsize=2)
def read_export(filename):
    return (RESULTS / filename).read_bytes()


def app(environ, start_response):
    """Preserve the /api prefix: service rewrites forward the original path."""
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    headers = [("Content-Type", "application/json; charset=utf-8")]
    status = "200 OK"
    if method not in {"GET", "HEAD"}:
        status, payload = "405 Method Not Allowed", {"error": "Use GET or HEAD."}
        headers.append(("Allow", "GET, HEAD"))
    elif path in EXPORTS:
        body = read_export(EXPORTS[path])
        payload = None
    elif path == "/api/health":
        payload = {"status": "ok"}
    elif path in {"/api", "/api/"}:
        payload = {"service": "app", "exports": list(EXPORTS)}
    else:
        status, payload = "404 Not Found", {"error": "Route not found."}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    headers.extend([
        ("Content-Length", str(len(body))),
        ("Cache-Control", "public, max-age=0, must-revalidate" if status == "200 OK" else "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    start_response(status, headers)
    return [body] if method != "HEAD" else []


if __name__ == "__main__":
    # Local preview only; Vercel loads the WSGI callable above in production.
    from wsgiref.simple_server import make_server

    with make_server("127.0.0.1", int(os.environ.get("PORT", "8000")), app) as server:
        server.serve_forever()
