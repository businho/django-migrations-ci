from pathlib import Path
from shutil import copyfile

from django.core.management import execute_from_command_line


def test_migrateci_postgresql(connection):
    execute_from_command_line(["manage.py", "migrateci", "--database", "postgresql"])
    with connection.cursor() as cursor:
        cursor.execute("select datname FROM pg_database")
        databases = {db for db, in cursor.fetchall()}
    assert "test_django" in databases


def test_migrateci_postgresql_parallel(connection):
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
    with connection.cursor() as cursor:
        cursor.execute("select datname FROM pg_database")
        databases = {db for db, in cursor.fetchall()}
    assert Path("migrateci-postgresql").exists()
    assert "test_django" in databases


def test_migrateci_cached(mocker):
    # Create empty cache file.
    basepath = Path(__file__).parent
    copyfile(basepath / "postgres_dump.sql", "migrateci-postgresql")
    setup_test_db_mock = mocker.patch("django_migrations_ci.django.setup_test_db")

    execute_from_command_line(["manage.py", "migrateci", "--database", "postgresql"])
    setup_test_db_mock.assert_not_called()
