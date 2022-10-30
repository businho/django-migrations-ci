from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connections
from django.test.runner import get_max_test_processes

from django_migrations_ci import django


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-n", "--parallel", default=None)
        parser.add_argument(
            "--pytest",
            dest="is_pytest",
            action="store_true",
            default=False,
        )
        parser.add_argument("--directory", default="")

    def handle(self, *args, parallel, is_pytest, directory, **options):
        if parallel == "auto":
            parallel = get_max_test_processes()
        elif parallel is not None:
            parallel = int(parallel)

        cached_files = {
            connection.alias: Path(directory) / Path(f"migrateci-{connection.alias}")
            for connection in connections.all()
        }

        if all(f.exists() for f in cached_files.values()):
            print("Database cache exists.")
            django.create_test_db()

            for connection in connections.all():
                backend = django.get_db_backend(connection)
                cached_file = cached_files[connection.alias]
                with django.test_db(connection):
                    backend.load(connection, cached_file)
        else:
            print("Database cache does not exist.")
            django.setup_test_db()

            for connection in connections.all():
                backend = django.get_db_backend(connection)
                cached_file = cached_files[connection.alias]
                with django.test_db(connection):
                    backend.dump(connection, cached_file)

        if parallel:
            for connection in connections.all():
                with django.test_db(connection):
                    django.clone_test_db(
                        connection=connection,
                        parallel=parallel,
                        is_pytest=is_pytest,
                    )
