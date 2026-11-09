"""Database fixtures cannot connect to the developer's configured MongoDB."""

from copy import deepcopy

import mongomock
import pytest

from starmap.migration import import_data, prepare_import


@pytest.fixture(scope="session")
def source_import():
    return prepare_import()


@pytest.fixture
def prepared(source_import):
    return deepcopy(source_import)


@pytest.fixture
def database(prepared):
    client = mongomock.MongoClient()
    database = client["isolated_starmap_tests"]
    import_data(database, prepared)
    yield database
    client.close()
