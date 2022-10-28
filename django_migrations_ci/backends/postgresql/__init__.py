from django.db import connections

from . import shell


def load(alias, input_file):
    """
    psql -h $HOST -p $PORT -U $USER -d test_foo -f migrate-postgresql
    """
    connection = connections[alias]
    shell.load(connection.settings_dict, input_file)


def dump(alias, output_file):
    """
    pg_dump -F c -h $DB_HOST -U $POSTGRES_USER test_foo -f migrateci-postgresql
    """
    connection = connections[alias]
    shell.dump(connection.settings_dict, output_file)
