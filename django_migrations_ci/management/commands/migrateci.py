import os

from django.core.management.base import BaseCommand
from django.db import connections

from django_migrations_ci import django
from django_migrations_ci.backends import sqlite3


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("parallel")
        # pytest-django uses test_db_gwN, from 1 to N worker processes.
        parser.add_argument("-s", "--suffix", default="")

    def handle(self, parallel, *args, suffix, **options):
        connection = connections["default"]
        test_db_name = connection.creation._get_test_db_name()
        cached_file = f"migrateci-{test_db_name}"

        backend = sqlite3

        if os.path.exists(cached_file):
            print("Database cache exists.")
            backend.load(test_db_name, cached_file)
        else:
            print("Database cache does not exist.")
            django.setup_test_db()
            backend.dump(test_db_name, cached_file)

        django.clone_test_db(parallel, suffix=suffix)
