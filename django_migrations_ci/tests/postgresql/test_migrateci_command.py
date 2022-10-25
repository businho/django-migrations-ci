from pathlib import Path

from django.conf import settings
from django.core.management import execute_from_command_line
import psycopg2


def test_migrateci():
    execute_from_command_line(["manage.py", "migrateci"])
    assert Path("dbtest.sqlite3").exists()
    assert not Path("dbtest_1.sqlite3").exists()


def test_migrateci_parallel():
    execute_from_command_line(["manage.py", "migrateci", "--parallel", "1"])
    assert Path("dbtest.sqlite3").exists()
    assert Path("dbtest_1.sqlite3").exists()
    assert not Path("dbtest_2.sqlite3").exists()


def test_migrateci_suffix():
    execute_from_command_line(
        [
            "manage.py",
            "migrateci",
            "--parallel",
            "1",
            "--suffix",
            "buser",
        ]
    )
    assert Path("dbtest.sqlite3").exists()
    assert Path("dbtest_buser1.sqlite3").exists()


def test_migrateci_cached(mocker):
    # Create empty cache file.
    Path("migrateci-default").touch()
    setup_test_db_mock = mocker.patch("django_migrations_ci.django.setup_test_db")

    execute_from_command_line(["manage.py", "migrateci"])

    assert Path("dbtest.sqlite3").exists()
    setup_test_db_mock.assert_not_called()


def test_migrateci_postgresql():
    execute_from_command_line(["manage.py", "migrateci", "--database", "postgresql"])

    db_conf = settings.DATABASES["postgresql"]
    conn = psycopg2.connect(
        "postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}".format(**db_conf)
    )
    with conn.cursor() as cursor:
        cursor.execute("select datname FROM pg_database")
        databases = {db for db, in cursor.fetchall()}
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

    conn = psycopg2.connect("postgresql://buser:buser@localhost/test_django")
    with conn.cursor() as cursor:
        cursor.execute("select datname FROM pg_database")
        databases = {db for db, in cursor.fetchall()}
    assert Path("migrateci-postgresql").exists()
    assert "test_django" in databases
