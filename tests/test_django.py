import pytest

import django as djangoframework
from django_migrations_ci import django


@pytest.mark.parametrize(
    "db_name,expected_db_name",
    [
        ("db", "db"),
        ("db_gw0", "db_gw0"),
        ("db_gw0.sqlite3", "db.sqlite3_gw0"),
        ("db_gw0..sqlite3", "db.sqlite3_gw0"),
    ],
)
def test_fix_sqlite_pytest_suffix(db_name, expected_db_name):
    assert django._fix_sqlite_pytest_suffix(db_name) == expected_db_name


@pytest.mark.parametrize(
    "db_name,expected_db_name",
    [
        ("db", "db"),
        ("db_1", "db_1"),
        ("db_1.sqlite3", "db_1.sqlite3"),
        ("db_gw0.sqlite3", "db.sqlite3_gw0"),
        ("db_gw0..sqlite3", "db.sqlite3_gw0"),
        ("db_gw12.sqlite3", "db.sqlite3_gw12"),
        # Django<4 bugs.
        ("db_1..sqlite3", "db_1..sqlite3"),
        ("db_1.", "db_1."),
    ],
)
def test_transform_sqlite_name(db_name, expected_db_name):
    assert django._transform_sqlite_db_name(db_name) == expected_db_name


def test_hash_files():
    djangoframework.setup()
    it = django.hash_files(1)
    assert next(it) == "8c1c0190533e18f1e694d8b0be5c46ad"
    assert next(it) == "e7cc3570aebddf921af899fc45ba3e9c"
    with pytest.raises(StopIteration):
        next(it)
