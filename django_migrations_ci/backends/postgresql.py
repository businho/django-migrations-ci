from subprocess import PIPE, Popen

from django.conf import settings


def _exec(command, env):
    p = Popen(
        command,
        shell=True,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        env=env,
    )
    resp = p.communicate()
    print("EXEC", command, resp)
    return resp


def load(alias, input_file):
    """
    psql -h $HOST -p $PORT -U $USER -c "DROP DATABASE IF EXISTS test_foo;"
    psql -h $HOST -p $PORT -U $USER -c "CREATE DATABASE test_foo;"
    psql -h $HOST -p $PORT -U $USER -d test_foo -f migrate-postgresql
    """
    db_conf = settings.DATABASES[alias]
    env = {"PGPASSWORD": db_conf["PASSWORD"]}
    base_command = "psql -h {HOST} -p {PORT} -U {USER}"

    psql = base_command + " -c 'DROP DATABASE IF EXISTS {NAME}'"
    _exec(psql.format(**db_conf), env)
    psql = base_command + " -c 'CREATE DATABASE {NAME}'"
    _exec(psql.format(**db_conf), env)

    psql = base_command + " -d {NAME} -f {input_file}"
    _exec(psql.format(**db_conf, input_file=input_file), env)


def dump(alias, output_file):
    """
    pg_dump -F c -h $DB_HOST -U $POSTGRES_USER test_foo -f migrateci-postgresql
    """
    db_conf = settings.DATABASES[alias]
    env = {"PGPASSWORD": db_conf["PASSWORD"]}

    pg_dump = "pg_dump -Fp -h {HOST} -p {PORT} -U {USER} -d {NAME} -f {output_file}"
    _exec(pg_dump.format(output_file=output_file, **db_conf), env)
