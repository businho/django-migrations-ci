import os
from pathlib import Path
import tempfile

import pytest


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


@pytest.fixture
def tempdir():
    directory = tempfile.TemporaryDirectory()
    with directory:
        yield directory.name
