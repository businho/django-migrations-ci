import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["DJANGO_SETTINGS_MODULE"] = "django_migrations_ci.tests.testapp.settings"


def _rm(filename):
    try:
        os.remove("migrateci-default")
    except FileNotFoundError:
        pass


@pytest.fixture(autouse=True)
def remove_cached_files():
    filename = "migrateci-default"
    _rm(filename)
    yield
    _rm(filename)


@pytest.fixture(autouse=True)
def remove_sqlite3_files():
    filename = "dbtest.sqlite3"
    _rm(filename)
    yield
    _rm(filename)
