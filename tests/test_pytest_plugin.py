import os
from io import StringIO
from unittest.mock import sentinel

import django as djangoframework
import pytest

from django_migrations_ci import pytest_plugin


@pytest.fixture(autouse=True)
def setup_django():
    djangoframework.setup()


@pytest.fixture
def config(mocker):
    return mocker.Mock(
        option=mocker.Mock(
            help=None,
            migrateci=True,
            migrateci_depth=None,
            migrateci_location=None,
            migrateci_storage=None,
            migrateci_verbose=None,
            numprocesses=None,
            verbose=1,
        ),
    )


@pytest.fixture
def call_comand_mock(mocker):
    return mocker.patch("django_migrations_ci.pytest_plugin.call_command")


def test_pytest_configure(config, call_comand_mock):
    pytest_plugin.pytest_configure(config)
    call_comand_mock.assert_called_with("migrateci", pytest=True, verbosity=1)


def test_pytest_configure_all_options(config, call_comand_mock):
    config.option.numprocesses = 2
    config.option.verbose = 3
    config.option.migrateci_storage = sentinel.migrateci_storage
    config.option.migrateci_location = "foo"
    config.option.migrateci_depth = 3
    pytest_plugin.pytest_configure(config)
    call_comand_mock.assert_called_with(
        "migrateci",
        pytest=True,
        storage_class=sentinel.migrateci_storage,
        location="foo",
        parallel=2,
        depth=3,
        verbosity=3,
    )


def test_pytest_xdist_worker_do_not_execute_command(config, call_comand_mock, mocker):
    mocker.patch.dict(os.environ, {"PYTEST_XDIST_WORKER": "42"})
    pytest_plugin.pytest_configure(config)
    call_comand_mock.assert_not_called()


expected_help = """usage: pytest [--migrateci] [--migrateci-location MIGRATECI_LOCATION]
              [--migrateci-storage MIGRATECI_STORAGE] [--migrateci-depth MIGRATECI_DEPTH]
              [--migrateci-verbose MIGRATECI_VERBOSE]
              [file_or_dir ...]

positional arguments:
  file_or_dir

migrateci:
  --migrateci           run migrateci before tests
  --migrateci-location=MIGRATECI_LOCATION
  --migrateci-storage=MIGRATECI_STORAGE
  --migrateci-depth=MIGRATECI_DEPTH
  --migrateci-verbose=MIGRATECI_VERBOSE
"""

def test_pytest_options():
    parser = pytest.Parser()
    pytest_plugin.pytest_addoption(parser)
    output = StringIO()
    parser._getparser().print_help(file=output)
    assert output.getvalue() == expected_help
