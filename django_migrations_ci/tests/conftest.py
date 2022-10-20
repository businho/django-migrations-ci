import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["DJANGO_SETTINGS_MODULE"] = "django_migrations_ci.tests.testapp.settings"
