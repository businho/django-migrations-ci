import os

from django.core.management import execute_from_command_line


def test_clone_database():
    # TODO: Cleanup files before the test.
    execute_from_command_line(["manage.py", "setup_test_db"])
    execute_from_command_line(["manage.py", "clone_test_db", "2", "--suffix", "foo"])
    assert os.path.exists("dbtest_foo1.sqlite3")
    assert os.path.exists("dbtest_foo2.sqlite3")
    assert not os.path.exists("dbtest_foo3.sqlite3")
