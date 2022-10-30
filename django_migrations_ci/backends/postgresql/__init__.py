from django_migrations_ci.backends.postgresql import shell


def dump(connection, output_file):
    """
    pg_dump -F c -h $DB_HOST -U $POSTGRES_USER test_foo -f migrateci-postgresql
    """
    shell.dump(connection.settings_dict, output_file)
