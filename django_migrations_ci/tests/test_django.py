import pytest

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
