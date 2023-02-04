import shutil
from pathlib import Path

from django.core.management import execute_from_command_line
from django.db import connections
from django.db.utils import OperationalError
import pytest

from django_migrations_ci import django

CHECKSUM_0001 = "e7cc3570aebddf921af899fc45ba3e9c"
CHECKSUM_0002 = "8c1c0190533e18f1e694d8b0be5c46ad"


def _check_db(connection, suffix=""):
    with django.test_db(connection, suffix=suffix):
        with connection.cursor() as conn:
            conn.execute("SELECT * FROM testapp_bus")
            result = conn.fetchall()
    assert list(result) == [(1, "BUS3R")]


def cli(*, parallel=None, pytest=False, location=None, depth=None, verbosity=None):
    args = ["manage.py", "migrateci"]
    if parallel is not None:
        args.append(f"--parallel={parallel}")
    if pytest:
        args.append("--pytest")
    if location:
        args.append(f"--location={location}")
    if verbosity:
        args.append(f"-v{verbosity}")
    if depth:
        args.append(f"--depth={depth}")

    execute_from_command_line(args)


def test_migrateci(tmpdir):
    cli(location=tmpdir)
    _check_db(connections["default"])


def test_migrateci_parallel(tmpdir):
    cli(location=tmpdir, parallel=1)
    connection = connections["default"]
    _check_db(connection)
    _check_db(connection, suffix="1")
    try:
        _check_db(connection, suffix="2")
    except OperationalError:
        pass
    else:  # pragma: nocover
        pytest.fail("Database 2 should not exist here.")


def test_migrateci_pytest(tmpdir):
    cli(location=tmpdir, parallel=1, pytest=True)
    connection = connections["default"]
    _check_db(connection)
    _check_db(connection, suffix="gw0")
    try:
        _check_db(connection, suffix="gw1")
    except OperationalError:
        pass
    else:  # pragma: nocover
        pytest.fail("Database gw1 should not exist here.")


def test_migrateci_cached(mocker, tmpdir):
    """Apply all cached migrations, no setup needed after that."""
    connection = connections["default"]
    migration_file = Path(__file__).parent / f"dump/0002/{connection.vendor}.sql"
    migration_cached = tmpdir / f"migrateci-default-{CHECKSUM_0002}"
    shutil.copyfile(migration_file, migration_cached)
    setup_test_db_mock = mocker.patch("django_migrations_ci.django.setup_test_db")
    cli(location=tmpdir)
    setup_test_db_mock.assert_not_called()
    _check_db(connections["default"])


def test_migrateci_cached_partial(mocker, tmpdir):
    """Apply one cached migration and setup after that."""
    connection = connections["default"]
    migration_file = Path(__file__).parent / f"dump/0001/{connection.vendor}.sql"
    migration_cached = tmpdir / f"migrateci-default-{CHECKSUM_0001}"
    shutil.copyfile(migration_file, migration_cached)
    load_spy = mocker.spy(django, "load")
    setup_test_db_spy = mocker.spy(django, "setup_test_db")
    cli(location=tmpdir, depth=1)
    setup_test_db_spy.assert_called_once()
    load_spy.assert_called_once()
    assert load_spy.call_args[0][1] == migration_cached.basename
    _check_db(connections["default"])


def test_migrateci_location(tmpdir):
    cli(location=tmpdir)
    _check_db(connections["default"])
    migration_cached = tmpdir / f"migrateci-default-{CHECKSUM_0002}"
    assert migration_cached.exists()


def test_migrateci_verbose(tmpdir):
    cli(location=tmpdir, verbosity=3)
    _check_db(connections["default"])
