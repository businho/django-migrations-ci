from django.apps import apps
from django.core.management import execute_from_command_line


def test_setup_database():
    execute_from_command_line(["manage.py", "setup_test_db"])
    # Migrations create one bus.
    Bus = apps.get_model("testapp", "Bus")
    assert Bus.objects.count() == 1
