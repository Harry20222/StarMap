"""Playwright's isolated Python/MongoDB API; never loads .env or live data."""

from pathlib import Path
import sys
from wsgiref.simple_server import WSGIRequestHandler, make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import mongomock
import app as web
from starmap.migration import import_data, prepare_import


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    client = mongomock.MongoClient()
    database = client["isolated_browser_tests"]
    import_data(database, prepare_import())
    web.get_database = lambda: database
    with make_server("127.0.0.1", 8001, web.app, handler_class=QuietHandler) as server:
        server.serve_forever()
