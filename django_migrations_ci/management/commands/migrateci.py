from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connections
from django.test.runner import get_max_test_processes

from django_migrations_ci import django


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")
        parser.add_argument("-n", "--parallel", default=None)
        # pytest-django uses test_db_gwN, from 1 to N worker processes.
        parser.add_argument("-s", "--suffix", default="")

    def handle(self, *args, database, parallel, suffix, **options):
        if parallel == "auto":
            parallel = get_max_test_processes()
        elif parallel is not None:
            parallel = int(parallel)

        connection = connections[database]
        cached_file = f"migrateci-{database}"

        backend = django.get_db_backend(connection)

        if Path(cached_file).exists():
            print("Database cache exists.")
            backend.load(database, cached_file)
        else:
            print("Database cache does not exist.")
            django.setup_test_db()
            backend.dump(database, cached_file)

        if parallel:
            django.clone_test_db(
                database=database,
                parallel=parallel,
                suffix=suffix,
            )
