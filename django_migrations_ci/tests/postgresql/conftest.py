from pathlib import Path

import pytest


def _rm(pathname):
    for filename in Path(".").glob(pathname):
        Path(filename).unlink()


@pytest.fixture(autouse=True)
def remove_sqlite3_files():
    pathname = "dbtest*.sqlite3"
    _rm(pathname)
    yield
    _rm(pathname)
