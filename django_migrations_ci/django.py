import hashlib
import importlib
import itertools
import logging
import os
import re
import tempfile
from contextlib import contextmanager
from unittest import mock

from django.conf import settings
from django.db import connections
from django.db.migrations.loader import MigrationLoader
from django.test.utils import setup_databases

logger = logging.getLogger(__name__)


def _get_db_backend(connection):
    vendor_map = {
        "mysql": "django_migrations_ci.backends.mysql",
        "postgresql": "django_migrations_ci.backends.postgresql",
        "sqlite": "django_migrations_ci.backends.sqlite",
    }
    return importlib.import_module(vendor_map[connection.vendor])


def create_test_db(connection, *, keepdb=False, verbosity=1):
    backend = _get_db_backend(connection)
    test_database_name = connection.creation._get_test_db_name()
    database_created = (
        not keepdb or not backend.database_exists(connection, test_database_name)
    )
    database_name = connection.creation._create_test_db(
        verbosity=verbosity, autoclobber=True, keepdb=keepdb
    )
    return database_name, database_created


def get_unique_connections():
    return [
        connection
        for connection in connections.all()
        if not connection.settings_dict.get("TEST", {}).get("MIRROR")
    ]


def setup_test_db(*, verbosity=1):
    # Based on https://github.com/django/django/blob/d62563cbb194c420f242bfced52b37d6638e67c6/django/test/runner.py#L1051-L1054  # noqa: E501
    unique_connections = get_unique_connections()
    database_names = {
        connection.alias: connection.settings_dict["NAME"]
        for connection in unique_connections
    }
    aliases = list(database_names.keys())
    setup_databases(
        aliases=aliases,
        verbosity=verbosity,
        interactive=False,
        keepdb=True,
    )

    # Django setup_databases change original settings and don't care about it
    # because it run the setup only one time and other parts of testing understand that.
    for connection in unique_connections:
        database_name = database_names[connection.alias]
        connection.close()
        settings.DATABASES[connection.alias]["NAME"] = database_name
        connection.settings_dict["NAME"] = database_name


def clone_test_db(connection, parallel, is_pytest=False, *, verbosity=1):
    for index in range(parallel):
        if is_pytest:
            # pytest-django use test_db_gwN, from 0 to N-1.
            # e.g. test_db_gw0, test_db_gw1, ...
            # https://github.com/pytest-dev/pytest-django/blob/e0c77b391ea54c3b8d6ffbb593aa25188a0ce7e9/pytest_django/fixtures.py#L61  # noqa: E501
            suffix = f"gw{index}"
        else:
            # Django use test_db_N, from 1 to N.
            # e.g. test_db_1, test_db_2, ...
            suffix = f"{index + 1}"

        connection.creation.clone_test_db(
            suffix=suffix, verbosity=verbosity, keepdb=False
        )

        if connection.vendor == "sqlite":
            settings_dict = connection.creation.get_test_db_clone_settings(suffix)
            django_db_name = settings_dict["NAME"]
            if is_pytest and "." in django_db_name:
                # Move db_gw0.sqlite3 to db.sqlite3_gw0.
                os.rename(django_db_name, _fix_sqlite_pytest_suffix(django_db_name))


def _fix_sqlite_pytest_suffix(db_name):
    # Django<4 generate sqlite3 names with two dots, like db_1..sqlite3,
    # it is cleaned here to db_1.sqlite3.
    clean_db_name = re.sub(r"\.+", ".", db_name)
    # Django clone_test_db create file db_gw0.sqlite3, but pytest-django
    # expects db.sqlite3_gw0. Lets rename the file.
    pytest_db_name = re.sub(r"(_gw\d+)(\.)+(.+)$", r".\3\1", clean_db_name)
    return pytest_db_name


@contextmanager
def test_db(connection, suffix=""):
    # Django clone_test_db trust setup_databases already changed original settings,
    # so I have to do that here.
    try:
        test_db_name = connection.settings_dict["TEST"]["NAME"]
    except KeyError:
        test_db_name = None

    if not test_db_name:
        test_db_name = connection.creation._get_test_db_name()

    if suffix:
        if connection.vendor == "sqlite":
            settings_dict = connection.creation.get_test_db_clone_settings(suffix)
            _generated_db_name = settings_dict["NAME"]
            # Django<4 generate sqlite3 names with two dots, like db_1..sqlite3,
            # or if it does not have an extension, database name will end with a dot.
            dotbug = ".." in _generated_db_name or _generated_db_name.endswith(".")
            test_db_name = _transform_sqlite_db_name(
                test_db_name, suffix=suffix, dotbug=dotbug
            )
        else:
            test_db_name += f"_{suffix}"

    db_name = connection.settings_dict["NAME"]
    connection.settings_dict["NAME"] = test_db_name
    settings.DATABASES[connection.alias]["NAME"] = test_db_name
    connection.close()

    try:
        yield
    finally:
        connection.settings_dict["NAME"] = db_name
        settings.DATABASES[connection.alias]["NAME"] = db_name
        connection.close()


def _transform_sqlite_db_name(db_name, *, suffix="", dotbug=False):
    if suffix:
        suffix = f"_{suffix}"
    if dotbug:
        suffix += "."

    # db.sqlite3_1 to db_1.sqlite3.
    db_name = re.sub(r"(.+)(\..+)$", rf"\1{suffix}\2", db_name)
    # db_gw1.sqlite3 to db.sqlite3_gw1
    db_name = re.sub(r"(_gw\d+)\.+(.+)$", r".\2\1", db_name)
    return db_name


def load(connection, input_file, storage, *, verbosity=1):
    if verbosity:
        db_name = connection.settings_dict["NAME"]
        logger.info(f"Load {input_file} to {db_name}")
    with storage.open(input_file, "r") as f:
        sql = f.read()
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            # sqlite3 can't use execute() to run many statements, it fails with
            # "sqlite3.Warning: You can only execute one statement at a time."
            cursor.executescript(sql)
        else:
            cursor.execute(sql)


def dump(connection, output_file, storage, *, verbosity=1):
    if verbosity:
        db_name = connection.settings_dict["NAME"]
        logger.info(f"Dump {db_name} to {output_file}.")

    backend = _get_db_backend(connection)

    # Dump to a temp file because backends expect a filename instead of a file object.
    _, tmp_filename = tempfile.mkstemp(prefix="migrateci", suffix=".sql")
    backend.dump(connection, tmp_filename)

    # Copy it to the storage.
    with (
        open(tmp_filename, "r") as tmp_fp,
        storage.open(output_file, "w") as output_fp,
    ):
        output_fp.write(tmp_fp.read())


def hash_files(depth=0):
    """
    Generate checksums based on migrations graph.

    Yield many checksums first based on all migrations, after that it tries to
    remove `depth` migrations per app.
    """
    loader = MigrationLoader(None, ignore_no_migrations=True)
    nodes = loader.graph.leaf_nodes()
    plan = loader.graph._generate_plan(nodes, at_end=True)

    checksums = {}
    for app_label, migration_name in plan:
        migration = loader.get_migration(app_label, migration_name)
        module = importlib.import_module(migration.__module__)
        filename = module.__file__

        # Calculate checksum for each migration to limit memory usage.
        with open(filename, "rb") as f:
            checksum = hashlib.md5(f.read()).hexdigest()

        app_checksums = checksums.setdefault(app_label, [])
        app_checksums.append(checksum)

    for n in range(0, depth + 1):
        combinations = itertools.combinations_with_replacement(checksums, n)
        for apps_to_remove_migration in combinations:
            copy_checksums = checksums.copy()
            for app_label in apps_to_remove_migration:
                # Remove last migration from selected app.
                remaining_checksums = copy_checksums[app_label][:-1]
                copy_checksums[app_label] = remaining_checksums

            checksum = hashlib.md5()
            for app_checksums in copy_checksums.values():
                checksum.update("".join(app_checksums).encode())
            yield checksum.hexdigest()
