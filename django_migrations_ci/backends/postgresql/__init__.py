from django.conf import settings

from . import shell


def load(alias, input_file):
    """
    psql -h $HOST -p $PORT -U $USER -c "DROP DATABASE IF EXISTS test_foo;"
    psql -h $HOST -p $PORT -U $USER -c "CREATE DATABASE test_foo;"
    psql -h $HOST -p $PORT -U $USER -d test_foo -f migrate-postgresql
    """
    db_conf = settings.DATABASES[alias]
    shell.drop_database(db_conf)
    shell.create_database(db_conf)
    shell.load(db_conf, input_file)


def dump(alias, output_file):
    """
    pg_dump -F c -h $DB_HOST -U $POSTGRES_USER test_foo -f migrateci-postgresql
    """
    db_conf = settings.DATABASES[alias]
    shell.dump(db_conf, output_file)
