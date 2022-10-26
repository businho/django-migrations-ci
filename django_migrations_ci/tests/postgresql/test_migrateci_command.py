import os
from pathlib import Path
from shutil import copyfile

from django.core.management import execute_from_command_line
import pytest

from django_migrations_ci.tests.postgresql import utils


@pytest.fixture
def db_name():
    # Do not use django settings here, because Django change it in runtime.
    return os.getenv("POSTGRES_DB", "postgres")


def test_migrateci_postgresql(db_name):
    execute_from_command_line(["manage.py", "migrateci", "--database", "postgresql"])
    assert Path("migrateci-postgresql").exists()
    databases = utils.databases()
    assert f"test_{db_name}" in databases


def test_migrateci_postgresql_parallel(db_name):
    execute_from_command_line(
        [
            "manage.py",
            "migrateci",
            "--parallel",
            "2",
            "--database",
            "postgresql",
        ]
    )
    databases = utils.databases()
    assert f"test_{db_name}" in databases
    assert f"test_{db_name}_1" in databases
    assert f"test_{db_name}_2" in databases
    assert f"test_{db_name}_3" not in databases


def test_migrateci_pytest(db_name):
    execute_from_command_line(
        [
            "manage.py",
            "migrateci",
            "--parallel",
            "1",
            "--pytest",
            "--database",
            "postgresql",
        ]
    )
    databases = utils.databases()
    assert f"test_{db_name}_gw0" in databases


def test_migrateci_cached(mocker):
    # Create empty cache file.
    basepath = Path(__file__).parent
    copyfile(basepath / "postgres_dump.sql", "migrateci-postgresql")
    setup_test_db_mock = mocker.patch("django_migrations_ci.django.setup_test_db")

    execute_from_command_line(["manage.py", "migrateci", "--database", "postgresql"])
    setup_test_db_mock.assert_not_called()
