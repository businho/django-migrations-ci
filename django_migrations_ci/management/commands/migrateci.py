import logging
from pathlib import Path

from django.core.files.storage import get_storage_class
from django.core.management.base import BaseCommand, CommandError

try:
    from django.test.runner import get_max_test_processes
except ImportError:
    # Django<4
    def get_max_test_processes():
        raise CommandError(
            "Django<4 do not implement get_max_test_processes."
            " Use --parallel $(nproc) to not depend on this."
        )


from django_migrations_ci import django
from django_migrations_ci.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-n", "--parallel", default=settings.parallel)
        parser.add_argument(
            "--pytest",
            dest="is_pytest",
            action="store_true",
            default=settings.is_pytest,
        )
        parser.add_argument(
            "--directory",
            dest="location",
            default=settings.location,
            help="Deprecated, use --location instead.",
        )
        parser.add_argument("--location", default=settings.location)
        parser.add_argument(
            "--storage",
            dest="storage_class",
            default=settings.storage_class,
            type=get_storage_class,
        )
        parser.add_argument("--depth", type=int, default=settings.depth)

    def _setup_logging(self):
        lib_logger = logging.getLogger("django_migrations_ci")
        lib_logger.setLevel(logging.INFO)
        lib_logger.addHandler(logging.StreamHandler())

    def handle(
        self,
        *args,
        parallel,
        is_pytest,
        location,
        storage_class,
        depth,
        verbosity,
        **options,
    ):
        self._setup_logging()

        if parallel == "auto":
            parallel = get_max_test_processes()
        elif parallel is not None:
            parallel = int(parallel)

        if location:
            location = str(Path(location).expanduser())
        else:
            default_storage_class = get_storage_class(
                "django.core.files.storage.FileSystemStorage"
            )
            if issubclass(storage_class, default_storage_class):
                location_path = Path("~/.migrateci").expanduser()
                location_path.mkdir(parents=True, exist_ok=True)
                location = str(location_path)

        if verbosity >= 2:
            logger.info(f"Using storage {storage_class=} on {location=}.")
        storage = storage_class(location=location)

        _, files = storage.listdir("")
        files = set(files)
        if verbosity >= 3:
            logger.info(f"Files in storage: {files}")

        unique_connections = django.get_unique_connections()

        current_checksum = None
        checksums = django.hash_files(depth)
        for cached_checksum in checksums:
            # Current checksum is the first result returned from hash_files.
            if current_checksum is None:
                current_checksum = cached_checksum
                if verbosity:
                    logger.info(f"Migrations current checksum is {current_checksum}.")

            cached_files = {
                connection.alias: f"migrateci-{connection.alias}-{cached_checksum}"
                for connection in unique_connections
            }
            if all(f in files for f in cached_files.values()):
                if verbosity:
                    logger.info(
                        f"Migrations cache found with checksum {cached_checksum}."
                    )
                if verbosity >= 3:
                    for other_checksum in checksums:
                        logger.info(
                            f"Calculated checksum {other_checksum} not evaluated."
                        )
                break

            if verbosity >= 2:
                logger.info(
                    f"Migrations cache NOT found for checksum {cached_checksum}."
                )

        else:
            cached_checksum = None
            cached_files = None
            if verbosity:
                logger.info("Database cache does not exist.")

        if cached_files:
            if verbosity >= 2:
                logger.info(f"Create test db from cache {cached_checksum=}.")
            django.create_test_db(verbosity=verbosity)
            for connection in unique_connections:
                cached_file = cached_files[connection.alias]
                with django.test_db(connection):
                    django.load(connection, cached_file, storage, verbosity=verbosity)

        if current_checksum != cached_checksum:
            if verbosity >= 2:
                logger.info(
                    f"Setup test db from {cached_checksum=} to {current_checksum=}."
                )

            django.setup_test_db(verbosity=verbosity)
            for connection in unique_connections:
                current_file = f"migrateci-{connection.alias}-{current_checksum}"
                with django.test_db(connection):
                    django.dump(connection, current_file, storage, verbosity=verbosity)

        if parallel:
            if verbosity >= 2:
                logger.info(f"Clone test db for {parallel=}.")
            for connection in unique_connections:
                with django.test_db(connection):
                    django.clone_test_db(
                        connection=connection,
                        parallel=parallel,
                        is_pytest=is_pytest,
                        verbosity=verbosity,
                    )
