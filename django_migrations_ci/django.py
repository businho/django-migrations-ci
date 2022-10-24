from django.conf import settings
from django.db import connections
from django.test.runner import get_max_test_processes
from django.test.utils import setup_databases

# TODO: Handle aliases.


def setup_test_db(database_alias="default"):
    # Based on https://github.com/django/django/blob/d62563cbb194c420f242bfced52b37d6638e67c6/django/test/runner.py#L1051-L1054  # noqa: E501
    setup_databases(verbosity=True, interactive=False, aliases=[database_alias])


def clone_test_db(parallel, suffix, database_alias="default"):
    if parallel == "auto":
        parallel = get_max_test_processes()
    else:
        parallel = int(parallel)

    connection = connections[database_alias]
    test_db_name = connection.creation._get_test_db_name()
    settings.DATABASES[connection.alias]["NAME"] = test_db_name

    # Based on https://github.com/pytest-dev/pytest-django/blob/e0c77b391ea54c3b8d6ffbb593aa25188a0ce7e9/pytest_django/fixtures.py#L61  # noqa: E501
    for index in range(1, parallel + 1):
        connection.creation.clone_test_db(
            suffix=f"{suffix}{index}",
            verbosity=True,
            keepdb=False,
        )
