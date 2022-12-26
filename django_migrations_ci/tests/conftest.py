import os
from pathlib import Path
import tempfile

import pytest

from django_migrations_ci import django


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["DJANGO_SETTINGS_MODULE"] = "django_migrations_ci.tests.testapp.settings"


def _rm(pathname):
    for filename in Path(".").glob(pathname):
        Path(filename).unlink()


@pytest.fixture(autouse=True)
def remove_cached_files():
    pathname = "migrateci-*"
    _rm(pathname)
    yield
    _rm(pathname)


@pytest.fixture(autouse=True)
def remove_sqlite3_files():
    pathname = "dbtest*.sqlite3*"
    _rm(pathname)
    yield
    _rm(pathname)


@pytest.fixture(autouse=True)
def drop_postgresql_test_databases():
    for connection in django.get_unique_connections():
        if connection.vendor != "postgresql":
            continue
        with connection.cursor() as cursor:
            cursor.execute("select datname FROM pg_database")
            dbs = {db for db, in cursor.fetchall()}

        for db in dbs:
            if db.startswith("test_"):
                connection.creation._destroy_test_db(db, verbosity=True)


@pytest.fixture(autouse=True)
def drop_test_databases(remove_sqlite3_files, drop_postgresql_test_databases):
    pass


@pytest.fixture
def tempdir():
    directory = tempfile.TemporaryDirectory()
    with directory:
        yield directory.name
