from django.core.management.base import BaseCommand
from django.test.utils import setup_databases


# TODO: No idea how to test it.
class Command(BaseCommand):
    """
    Use Django to setup databases.
    """

    def handle(self, *args, **options):
        # Based on https://github.com/django/django/blob/d62563cbb194c420f242bfced52b37d6638e67c6/django/test/runner.py#L1051-L1054
        # TODO: Handle aliases better.
        setup_databases(verbosity=True, interactive=False, aliases=["default"])
