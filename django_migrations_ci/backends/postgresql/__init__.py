from django_migrations_ci.backends.postgresql import shell


def load(connection, input_file):
    """
    psql -h $HOST -p $PORT -U $USER -d test_foo -f migrate-postgresql
    """
    with open(input_file, "r") as f:
        sql = f.read()
    with connection.cursor() as cursor:
        cursor.execute(sql)


def dump(connection, output_file):
    """
    pg_dump -F c -h $DB_HOST -U $POSTGRES_USER test_foo -f migrateci-postgresql
    """
    shell.dump(connection.settings_dict, output_file)
