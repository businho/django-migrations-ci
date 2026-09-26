import contextlib
import os
from pathlib import Path

import pytest
from django.db import DatabaseError

from django_migrations_ci import django
from django_migrations_ci.backends import oracle


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.testapp.settings"


def _rm(pathname):
    for filename in Path().glob(pathname):
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
            dbs = {db for (db,) in cursor.fetchall()}

        for db in dbs:
            if db.startswith("test_"):
                connection.creation._destroy_test_db(db, verbosity=True)


@pytest.fixture(autouse=True)
def drop_oracle_test_user():
    for connection in django.get_unique_connections():
        if connection.vendor != "oracle":
            continue
        # A failed test may leave the connection as the test user.
        oracle.restore_user(connection)
        params = connection.creation._get_test_db_params()
        with connection.cursor() as cursor:
            for statement in (
                "DROP USER %(user)s CASCADE",
                "DROP TABLESPACE %(tblspace)s INCLUDING CONTENTS AND DATAFILES",
                "DROP TABLESPACE %(tblspace_temp)s INCLUDING CONTENTS AND DATAFILES",
            ):
                with contextlib.suppress(DatabaseError):
                    cursor.execute(statement % params)


@pytest.fixture(autouse=True)
def drop_test_databases(
    remove_sqlite3_files,
    drop_postgresql_test_databases,
    drop_oracle_test_user,
):
    pass
