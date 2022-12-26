from pathlib import Path

from django.core.management.base import BaseCommand

try:
    from django.test.runner import get_max_test_processes
except ImportError:
    # Django<4
    def get_max_test_processes():
        raise Exception(
            "Django<4 do not implement get_max_test_processes."
            " Use --parallel $(nproc) to not depend on this."
        )


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
        parser.add_argument("--local", action="store_true", default=False)

    def handle(
        self, *args, parallel, is_pytest, local, directory, verbosity, **options
    ):
        if parallel == "auto":
            parallel = get_max_test_processes()
        elif parallel is not None:
            parallel = int(parallel)

        suffix = ""
        if local:
            suffix = f"-{django.hash_files()}"

        unique_connections = django.get_unique_connections()
        cached_files = {
            connection.alias: Path(directory) / f"migrateci-{connection.alias}{suffix}"
            for connection in unique_connections
        }

        if all(f.exists() for f in cached_files.values()):
            print("Database cache exists.")
            django.create_test_db(verbosity=verbosity)

            for connection in unique_connections:
                cached_file = cached_files[connection.alias]
                with django.test_db(connection):
                    django.load(connection, cached_file)
        else:
            print("Database cache does not exist.")
            django.setup_test_db(verbosity=verbosity)

            for connection in unique_connections:
                cached_file = cached_files[connection.alias]
                with django.test_db(connection):
                    django.dump(connection, cached_file)

        if parallel:
            for connection in unique_connections:
                with django.test_db(connection):
                    django.clone_test_db(
                        connection=connection,
                        parallel=parallel,
                        is_pytest=is_pytest,
                        verbosity=verbosity,
                    )
