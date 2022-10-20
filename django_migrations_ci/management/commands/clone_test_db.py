from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.test.runner import get_max_test_processes


class Command(BaseCommand):
    """
    Copy the test database to support parallel tests.
    """

    def add_arguments(self, parser):
        parser.add_argument("parallel")
        # pytest-django uses test_db_gwN, from 1 to N worker processes.
        parser.add_argument("-s", "--suffix", default="")

    def handle(self, parallel, *args, suffix, **options):
        if parallel == "auto":
            parallel = get_max_test_processes()
        else:
            parallel = int(parallel)

        connection = connections["default"]
        settings.DATABASES[connection.alias][
            "NAME"
        ] = connection.creation._get_test_db_name()

        # https://github.com/pytest-dev/pytest-django/blob/e0c77b391ea54c3b8d6ffbb593aa25188a0ce7e9/pytest_django/fixtures.py#L61
        for index in range(1, parallel + 1):
            connection.creation.clone_test_db(
                suffix=f"{suffix}{index}",
                verbosity=True,
                keepdb=False,
            )
