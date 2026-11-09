from copy import deepcopy
import json
from unittest.mock import Mock

import mongomock
import pytest
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

from starmap import database as connection
from starmap.migration import ROOT, import_data, prepare_import, verify_import


def test_import_twice_preserves_every_field_and_unrelated_records(prepared):
    database = mongomock.MongoClient()["isolated_migration"]
    database.galaxies.insert_one({"galaxy_id": "unrelated:1", "untouched": True})
    database.maps.insert_one({"map_id": "unrelated", "untouched": True})
    database.map_markers.insert_one({"map_id": "unrelated", "galaxy_id": "unrelated:1", "x": 5})
    database.notes.insert_one({"untouched": True})
    first = import_data(database, prepared)
    assert first["imported"]["galaxies"]["inserted"] == 43
    assert first["imported"]["map_markers"]["inserted"] == 43
    second = import_data(database, prepared)
    assert all(c["inserted"] == c["modified"] == 0 for c in second["imported"].values())
    assert verify_import(database, prepared) == {"maps": 1, "galaxies": 43, "map_markers": 43}
    assert database.galaxies.count_documents({}) == 44
    assert database.map_markers.count_documents({}) == 44
    assert database.maps.count_documents({}) == 2
    assert database.notes.find_one()["untouched"]
    assert database.maps.find_one({"map_id": "unrelated"})["untouched"]
    assert database.galaxies.find_one({"galaxy_id": "unrelated:1"})["untouched"]
    # Upserts restore owned fields and preserve unrelated fields on owned records.
    gid = prepared["galaxies"][0]["galaxy_id"]
    database.galaxies.update_one({"galaxy_id": gid}, {"$set": {"redshift": 0, "private_note": "keep"}})
    import_data(database, prepared)
    assert database.galaxies.find_one({"galaxy_id": gid})["private_note"] == "keep"


def test_unique_indexes_and_map_specific_positions(database, prepared):
    galaxy, marker = prepared["galaxies"][0], prepared["markers"][0]
    for collection, record in ((database.galaxies, galaxy), (database.maps, prepared["map"]), (database.map_markers, marker)):
        with pytest.raises(DuplicateKeyError):
            collection.insert_one(deepcopy(record))
    database.map_markers.insert_one({**marker, "map_id": "another-map", "x": 1})
    assert database.map_markers.count_documents({"galaxy_id": galaxy["galaxy_id"]}) == 2


@pytest.mark.parametrize("kind", ["duplicate", "metadata", "outside", "nan", "origin", "missing"])
def test_invalid_sources_rejected_before_database_access(tmp_path, kind):
    (tmp_path / "data").mkdir()
    (tmp_path / "results").mkdir()
    sample = json.loads((ROOT / "data/sample.json").read_text())
    markers = json.loads((ROOT / "results/markers.json").read_text())
    measurements = json.loads((ROOT / "results/measurements.json").read_text())
    if kind == "duplicate":
        sample["galaxies"][1] = sample["galaxies"][0]
    elif kind == "metadata":
        sample["galaxies"][0]["redshift"] += 1
    elif kind == "outside":
        markers["markers"][0]["x"] = 3000
    elif kind == "nan":
        markers["markers"][0]["x"] = float("nan")
    elif kind == "origin":
        markers["pixel_origin"] = 1
    else:
        markers["markers"].pop()
    for file, value in (("data/sample.json", sample), ("results/markers.json", markers), ("results/measurements.json", measurements)):
        (tmp_path / file).write_text(json.dumps(value))
    with pytest.raises(ValueError):
        prepare_import(tmp_path)


def test_unexpected_map_markers_do_not_get_deleted(database, prepared):
    database.map_markers.insert_one({"map_id": "goods-s", "galaxy_id": "extra:1"})
    with pytest.raises(ValueError, match="unexpected"):
        import_data(database, prepared)
    assert database.map_markers.find_one({"galaxy_id": "extra:1"})


def test_connection_reuse_environment_precedence_and_timeouts(monkeypatch):
    connection.close_client()
    monkeypatch.setattr(connection, "load_dotenv", Mock())
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "isolated_client_test")
    client = Mock()
    constructor = Mock(return_value=client)
    monkeypatch.setattr(connection, "MongoClient", constructor)
    try:
        connection.get_database()
        connection.get_database()
        assert constructor.call_count == 1
        options = constructor.call_args.kwargs
        assert options["connectTimeoutMS"] == options["serverSelectionTimeoutMS"] == 5000
        assert options["timeoutMS"] == 8000 and options["connect"] is False
        connection.load_dotenv.assert_called_with(ROOT / ".env", override=False)
        client.get_database.assert_called_with("isolated_client_test")
        monkeypatch.setattr(connection.os, "getpid", lambda: -1)
        connection.get_database()
        assert constructor.call_count == 2
    finally:
        connection.close_client()


@pytest.mark.parametrize("setting", ["MONGODB_URI", "MONGODB_DATABASE"])
def test_both_settings_required_without_defaults(monkeypatch, setting):
    monkeypatch.setattr(connection, "load_dotenv", Mock())
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "isolated_client_test")
    monkeypatch.delenv(setting)
    with pytest.raises(connection.DatabaseConfigurationError):
        connection.get_database()


def test_real_driver_connection_failure_is_bounded():
    # Closed loopback port, never the developer's database or credentials.
    from pymongo import MongoClient
    with MongoClient("mongodb://127.0.0.1:1", serverSelectionTimeoutMS=100, connectTimeoutMS=100, timeoutMS=200) as client:
        with pytest.raises(ServerSelectionTimeoutError):
            client["isolated_failure_test"].command("ping")
