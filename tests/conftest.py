import contextlib
import os
from pathlib import Path

import django as django_framework
import pytest
from django.conf import settings as django_settings
from django.core.management import call_command
from django.db import connections

from django_migrations_ci import django
from django_migrations_ci.backends import oracle as oracle_backend


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


_ORACLE_INITIAL_SETTINGS = {}


def _snapshot_oracle_settings(connection):
    return _ORACLE_INITIAL_SETTINGS.setdefault(
        connection.alias,
        {
            "USER": connection.settings_dict["USER"],
            "PASSWORD": connection.settings_dict["PASSWORD"],
        },
    )


def _restore_oracle_settings(connection):
    snapshot = _snapshot_oracle_settings(connection)
    for dict_ in (
        connection.settings_dict,
        django_settings.DATABASES[connection.alias],
    ):
        dict_["USER"] = snapshot["USER"]
        dict_["PASSWORD"] = snapshot["PASSWORD"]
        dict_.pop("SAVED_USER", None)
        dict_.pop("SAVED_PASSWORD", None)

    connection.close()
    creation = connection.creation
    if "_maindb_connection" in creation.__dict__:
        with contextlib.suppress(Exception):
            creation._maindb_connection.close()
        del creation.__dict__["_maindb_connection"]


@pytest.fixture(autouse=True)
def drop_oracle_test_schemas():
    oracle_connections = [
        c for c in django.get_unique_connections() if c.vendor == "oracle"
    ]
    for connection in oracle_connections:
        _snapshot_oracle_settings(connection)
        _restore_oracle_settings(connection)
        _drop_oracle_test_objects(connection)
    yield
    for connection in oracle_connections:
        _restore_oracle_settings(connection)
        _drop_oracle_test_objects(connection)


def _drop_oracle_test_objects(connection):
    test_user = connection.creation._test_database_user()
    test = connection.settings_dict["TEST"]
    tblspace = test.get("TBLSPACE") or f"test_{test_user}"
    tblspace_tmp = test.get("TBLSPACE_TMP") or f"test_{test_user}_temp"
    drop_tblspace = "INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS"
    statements = [
        f"DROP USER {test_user} CASCADE",
        f"DROP TABLESPACE {tblspace} {drop_tblspace}",
        f"DROP TABLESPACE {tblspace_tmp} {drop_tblspace}",
    ]
    maindb = connection.creation._maindb_connection
    with maindb.cursor() as cursor:
        for statement in statements:
            # Ignore "user/tablespace does not exist" on fresh runs.
            with contextlib.suppress(Exception):
                cursor.execute(statement)
    maindb.close()
    if "_maindb_connection" in connection.creation.__dict__:
        del connection.creation.__dict__["_maindb_connection"]


@pytest.fixture(autouse=True)
def drop_test_databases(
    remove_sqlite3_files,
    drop_postgresql_test_databases,
    drop_oracle_test_schemas,
):
    pass


@pytest.fixture(scope="session", autouse=True)
def _generate_oracle_dump_files(setup_env):
    """For oracle vendor, pre-generate dump files used by cached tests."""
    django_framework.setup()
    connection = connections["default"]
    if connection.vendor != "oracle":
        return

    dump_dir = Path(__file__).parent / "dump"
    targets = [
        ("0001", ("testapp", "0001_initial")),
        ("0002", ("testapp", "0002_create_bus")),
    ]
    missing = [
        (checksum, migration)
        for checksum, migration in targets
        if not (dump_dir / checksum / "oracle.sql").exists()
    ]
    if not missing:
        return

    _snapshot_oracle_settings(connection)

    for checksum, (app_label, migration_name) in missing:
        _restore_oracle_settings(connection)
        _drop_oracle_test_objects(connection)

        connection.creation._create_test_db(
            verbosity=0,
            autoclobber=True,
            keepdb=False,
        )
        try:
            call_command("migrate", app_label, migration_name, verbosity=0)

            target_dir = dump_dir / checksum
            target_dir.mkdir(parents=True, exist_ok=True)
            oracle_backend.dump(connection, str(target_dir / "oracle.sql"))
        finally:
            connection.creation._destroy_test_db(
                connection.settings_dict["NAME"], verbosity=0,
            )

    _restore_oracle_settings(connection)
