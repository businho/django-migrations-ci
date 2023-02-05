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
            migrateci=True,
            numprocesses=None,
            verbose=1,
            migrateci_storage=None,
            migrateci_location=None,
            migrateci_depth=None,
        ),
    )


def test_pytest_configure(config, mocker):
    call_comand_mock = mocker.patch("django_migrations_ci.pytest_plugin.call_command")
    pytest_plugin.pytest_configure(config)
    call_comand_mock.assert_called_with("migrateci", pytest=True, verbosity=1)


def test_pytest_configure_all_options(config, mocker):
    config.option.numprocesses = 2
    config.option.verbose = 3
    config.option.migrateci_storage = sentinel.migrateci_storage
    config.option.migrateci_location = "foo"
    config.option.migrateci_depth = 3
    call_comand_mock = mocker.patch("django_migrations_ci.pytest_plugin.call_command")
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
