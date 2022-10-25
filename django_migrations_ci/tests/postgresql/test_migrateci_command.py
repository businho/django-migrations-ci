from pathlib import Path
from shutil import copyfile

from django.core.management import execute_from_command_line

from django_migrations_ci.tests.postgresql import utils


def test_migrateci_postgresql():
    execute_from_command_line(["manage.py", "migrateci", "--database", "postgresql"])
    assert Path("migrateci-postgresql").exists()
    databases = utils.databases()
    assert "test_django" in databases


def test_migrateci_postgresql_parallel():
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
    assert "test_django" in databases
    assert "test_django_1" in databases
    assert "test_django_2" in databases
    assert "test_django_3" not in databases


def test_migrateci_suffix():
    execute_from_command_line(
        [
            "manage.py",
            "migrateci",
            "--parallel",
            "1",
            "--suffix",
            "buser",
            "--database",
            "postgresql",
        ]
    )
    databases = utils.databases()
    assert "test_django_buser1" in databases


def test_migrateci_cached(mocker):
    # Create empty cache file.
    basepath = Path(__file__).parent
    copyfile(basepath / "postgres_dump.sql", "migrateci-postgresql")
    setup_test_db_mock = mocker.patch("django_migrations_ci.django.setup_test_db")

    execute_from_command_line(["manage.py", "migrateci", "--database", "postgresql"])
    setup_test_db_mock.assert_not_called()
