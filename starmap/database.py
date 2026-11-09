"""Server-only MongoDB configuration and one pooled client per process."""

import atexit
import os
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


class DatabaseConfigurationError(ValueError):
    pass


_lock = Lock()
_client = None
_client_key = None


def get_database():
    """Environment wins over local .env; neither setting has a default."""
    global _client, _client_key
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    uri = os.environ.get("MONGODB_URI", "").strip()
    name = os.environ.get("MONGODB_DATABASE", "").strip()
    if not uri or not name:
        raise DatabaseConfigurationError("Set MONGODB_URI and MONGODB_DATABASE on the Python service.")
    key = (os.getpid(), uri, name)
    with _lock:
        if _client is None or _client_key != key:
            if _client is not None and _client_key[0] == os.getpid():
                _client.close()
            # Clients are created after process startup and never reused after fork.
            client = MongoClient(
                uri, appname="StarMap", connect=False,
                serverSelectionTimeoutMS=5000, connectTimeoutMS=5000,
                socketTimeoutMS=5000, waitQueueTimeoutMS=2000,
                timeoutMS=8000, maxPoolSize=10,
            )
            try:
                database = client.get_database(name)
            except (PyMongoError, ValueError):
                client.close()
                raise DatabaseConfigurationError("Invalid database settings.") from None
            _client, _client_key = client, key
        else:
            database = _client.get_database(name)
    return database


def close_client():
    global _client, _client_key
    with _lock:
        if _client is not None:
            _client.close()
        _client = _client_key = None


atexit.register(close_client)
