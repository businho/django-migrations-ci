import os
from pathlib import Path
import tempfile

from django.conf import settings
from django.db import connections
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["DJANGO_SETTINGS_MODULE"] = "django_migrations_ci.tests.testapp.settings"


@pytest.fixture(autouse=True)
def reset_database_name():
    for connection in connections.all():
        settings_dict = settings.DATABASES[connection.alias]

        # Override database name with test database name.
        database_name = settings_dict["NAME"]
        settings_dict["ORIGINAL_NAME"] = database_name

        test_database_name = connection.creation._get_test_db_name()
        connection.close()

        print("DB", database_name, test_database_name)
        settings_dict["NAME"] = test_database_name
        connection.settings_dict["NAME"] = test_database_name
        settings_test_dict = connection.settings_dict.setdefault("TEST", {})
        settings_test_dict["NAME"] = test_database_name

    yield

    for connection in connections.all():
        connection.close()

        settings_dict = settings.DATABASES[connection.alias]
        database_name = settings_dict["ORIGINAL_NAME"]
        settings_dict["NAME"] = database_name
        connection.settings_dict["NAME"] = database_name


def _rm(pathname):
    for filename in Path(".").glob(pathname):
        Path(filename).unlink()


@pytest.fixture(autouse=True)
def remove_cached_files():
    pathname = "migrateci-*"
    _rm(pathname)
    yield
    _rm(pathname)


@pytest.fixture
def tempdir():
    directory = tempfile.TemporaryDirectory()
    with directory:
        yield directory.name
