import itertools

from django.core.files.storage import get_storage_class
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
        parser.add_argument(
            "--storage-class",
            default="django.core.files.storage.FileSystemStorage",
            type=get_storage_class,
        )
        parser.add_argument("--depth", type=int, default=1)

    def handle(
        self,
        *args,
        parallel,
        is_pytest,
        directory,
        storage_class,
        depth,
        verbosity,
        **options,
    ):
        if parallel == "auto":
            parallel = get_max_test_processes()
        elif parallel is not None:
            parallel = int(parallel)

        storage = storage_class(directory)
        _, files = storage.listdir("")
        files = set(files)

        unique_connections = django.get_unique_connections()

        current_checksum = None
        for cached_checksum in itertools.islice(django.hash_files(), depth):
            # Current checksum is the first result returned from hash_files.
            if current_checksum is None:
                current_checksum = cached_checksum

            cached_files = {
                connection.alias: f"migrateci-{connection.alias}-{cached_checksum}"
                for connection in unique_connections
            }
            if all(f in files for f in cached_files.values()):
                print("Database cache exists.")
                break
        else:
            cached_checksum = None
            cached_files = None
            print("Database cache does not exist.")

        if cached_files:
            django.create_test_db(verbosity=verbosity)
            for connection in unique_connections:
                cached_file = cached_files[connection.alias]
                with django.test_db(connection):
                    django.load(connection, cached_file, storage)

        if current_checksum != cached_checksum:
            django.setup_test_db(verbosity=verbosity)
            for connection in unique_connections:
                current_file = f"migrateci-{connection.alias}-{current_checksum}"
                with django.test_db(connection):
                    django.dump(connection, current_file, storage)

        if parallel:
            for connection in unique_connections:
                with django.test_db(connection):
                    django.clone_test_db(
                        connection=connection,
                        parallel=parallel,
                        is_pytest=is_pytest,
                        verbosity=verbosity,
                    )
