from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
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
        parser.add_argument("--directory", default="")

    def handle(self, *args, database, parallel, is_pytest, directory, **options):
        if parallel == "auto":
            parallel = get_max_test_processes()
        elif parallel is not None:
            parallel = int(parallel)

        connection = connections[database]
        cached_file = Path(directory) / Path(f"migrateci-{database}")

        backend = django.get_db_backend(connection)

        if Path(cached_file).exists():
            print("Database cache exists.")
            django.create_test_db()
            with _override_test_db(connection):
                backend.load(connection, cached_file)
        else:
            print("Database cache does not exist.")
            django.setup_test_db()
            backend.dump(connection, cached_file)

        if parallel:
            with _override_test_db(connection):
                django.clone_test_db(
                    connection=connection,
                    parallel=parallel,
                    is_pytest=is_pytest,
                )


@contextmanager
def _override_test_db(connection):
    # Django clone_test_db trust setup_databases already changed original settings,
    # so I have to do that here.
    try:
        test_db_name = connection.settings_dict["TEST"]["NAME"]
    except KeyError:
        test_db_name = None

    if not test_db_name:
        test_db_name = connection.creation._get_test_db_name()

    db_name = connection.settings_dict["NAME"]
    connection.settings_dict["NAME"] = test_db_name
    settings.DATABASES[connection.alias]["NAME"] = test_db_name
    connection.close()

    yield

    connection.settings_dict["NAME"] = db_name
    settings.DATABASES[connection.alias]["NAME"] = db_name
    connection.close()
