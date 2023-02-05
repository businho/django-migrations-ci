import os
from contextlib import nullcontext

from django.core.management import call_command


def pytest_addoption(parser):
    group = parser.getgroup("migrateci")
    group.addoption(
        "--migrateci", action="store_true", help="run migrateci before tests"
    )
    group.addoption("--migrateci-location")
    group.addoption("--migrateci-storage")
    group.addoption("--migrateci-depth", type=int)


def pytest_configure(config):
    if not config.option.migrateci:
        return

    try:
        from pytest_django.plugin import _blocking_manager

        db_unblock = _blocking_manager.unblock
    except ImportError:
        # The pytest-django lib is not installed, do nothing and hope for the best.
        db_unblock = nullcontext

    # I want to execute only on controller (without worker_id) to avoid multiple runs.
    # It also works without pytest-xdist.
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is not None:
        return

    command_kwargs = {"pytest": True, "verbosity": config.option.verbose}

    # Option numprocesses is from pytest-xdist and doesn't exist if it is not installed.
    parallel = getattr(config.option, "numprocesses", None)
    if parallel:
        command_kwargs["parallel"] = parallel

    # Option reuse_db is from pytest-django.
    create_db = config.option.create_db

    # Make pytest-django never create db because migrateci already do it.
    config.option.create_db = False

    reuse_db = getattr(config.option, "reuse_db", False)
    if reuse_db and not create_db:
        command_kwargs["reuse_db"] = True

    if config.option.migrateci_location:
        command_kwargs["location"] = config.option.migrateci_location
    if config.option.migrateci_storage:
        command_kwargs["storage_class"] = config.option.migrateci_storage
    if config.option.migrateci_depth:
        command_kwargs["depth"] = config.option.migrateci_depth

    with db_unblock():
        call_command("migrateci", **command_kwargs)
