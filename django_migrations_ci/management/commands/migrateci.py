from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connections
from django.test.runner import get_max_test_processes

from django_migrations_ci import django


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")
        parser.add_argument("-n", "--parallel", default=None)
        parser.add_argument(
            "--pytest",
            dest="is_pytest",
            action="store_true",
            default=False,
        )

    def handle(self, *args, database, parallel, is_pytest, **options):
        if parallel == "auto":
            parallel = get_max_test_processes()
        elif parallel is not None:
            parallel = int(parallel)

        connection = connections[database]
        cached_file = f"migrateci-{database}"

        backend = django.get_db_backend(connection)

        if Path(cached_file).exists():
            print("Database cache exists.")
            django.create_test_db()
            backend.load(database, cached_file)
        else:
            print("Database cache does not exist.")
            django.setup_test_db()
            backend.dump(database, cached_file)

        if parallel:
            django.clone_test_db(
                database=database,
                parallel=parallel,
                is_pytest=is_pytest,
            )
