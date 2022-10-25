from subprocess import PIPE, Popen

from django.conf import settings


def load(alias, input_file):
    """
    psql -h $DB_HOST -U $POSTGRES_USER -c "CREATE DATABASE test_foo;"
    pg_restore -h $DB_HOST -U $POSTGRES_USER -d test_foo migrateci-default.sql
    """
    # TODO


def dump(alias, output_file):
    """
    pg_dump -F c -h $DB_HOST -U $POSTGRES_USER test_foo > $BUILD_DIR/migrateci-default
    """
    db_conf = settings.DATABASES[alias]
    pg_dump = "pg_dump -Fc -h {HOST} -p {PORT} -U {USER} -d {NAME} -f {output_file}"
    p = Popen(
        pg_dump.format(output_file=output_file, **db_conf),
        shell=True,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        env={
            "PGPASSWORD": db_conf["PASSWORD"],
        },
    )
    p.communicate()
