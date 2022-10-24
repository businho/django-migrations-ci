import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["DJANGO_SETTINGS_MODULE"] = "django_migrations_ci.tests.testapp.settings"


@pytest.fixture(autouse=True)
def remove_cached_files():
    os.remove("migrateci-default")


@pytest.fixture(autouse=True)
def remove_sqlite3_files():
    filename = "dbtest.sqlite3"
    if os.path.exists(filename):
        os.remove(filename)
