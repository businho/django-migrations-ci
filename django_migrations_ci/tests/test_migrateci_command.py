import shutil
from pathlib import Path

from django.core.management import execute_from_command_line
from django.db import connections
from django.db.utils import OperationalError
import pytest

from django_migrations_ci import django


def _check_db(connection, suffix=""):
    with django.test_db(connection, suffix=suffix):
        with connection.cursor() as conn:
            conn.execute("SELECT * FROM testapp_bus")
            result = conn.fetchall()
    assert list(result) == [(1, "BUS3R")]


def test_migrateci():
    execute_from_command_line(["manage.py", "migrateci"])
    _check_db(connections["default"])


def test_migrateci_parallel():
    execute_from_command_line(["manage.py", "migrateci", "--parallel", "1"])
    connection = connections["default"]
    _check_db(connection)
    _check_db(connection, suffix="1")
    try:
        _check_db(connection, suffix="2")
    except OperationalError:
        pass
    else:  # pragma: nocover
        pytest.fail("Database 2 should not exist here.")


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
    connection = connections["default"]
    _check_db(connection)
    _check_db(connection, suffix="gw0")
    try:
        _check_db(connection, suffix="gw1")
    except OperationalError:
        pass
    else:  # pragma: nocover
        pytest.fail("Database gw1 should not exist here.")


def test_migrateci_cached(mocker):
    # Create empty cache file.
    basepath = Path(__file__).parent
    connection = connections["default"]
    shutil.copyfile(basepath / f"dump/{connection.vendor}.sql", "migrateci-default")
    setup_test_db_mock = mocker.patch("django_migrations_ci.django.setup_test_db")
    execute_from_command_line(["manage.py", "migrateci"])
    setup_test_db_mock.assert_not_called()
    _check_db(connections["default"])


def test_migrateci_local():
    execute_from_command_line(["manage.py", "migrateci", "--local"])
    _check_db(connections["default"])
    checksum = "b2bed1815363a843fdc8403d36497ddd"
    assert Path(f"migrateci-default-{checksum}").exists()
