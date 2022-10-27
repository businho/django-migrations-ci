from pathlib import Path

from django.core.management import execute_from_command_line


def test_migrateci():
    execute_from_command_line(["manage.py", "migrateci"])
    assert Path("dbtest.sqlite3").exists()
    assert not Path("dbtest_1.sqlite3").exists()


def test_migrateci_parallel():
    execute_from_command_line(["manage.py", "migrateci", "--parallel", "1"])
    assert Path("dbtest.sqlite3").exists()
    assert Path("dbtest_1.sqlite3").exists()
    assert not Path("dbtest_2.sqlite3").exists()


def test_migrateci_pytest():
    execute_from_command_line(
        [
            "manage.py",
            "migrateci",
            "--parallel",
            "1",
            "--pytest",
        ]
    )
    assert Path("dbtest.sqlite3").exists()
    assert Path("dbtest.sqlite3_gw0").exists()


def test_migrateci_cached(mocker):
    # Create empty cache file.
    Path("migrateci-default").touch()
    setup_test_db_mock = mocker.patch("django_migrations_ci.django.setup_test_db")
    execute_from_command_line(["manage.py", "migrateci"])
    assert Path("dbtest.sqlite3").exists()
    setup_test_db_mock.assert_not_called()
