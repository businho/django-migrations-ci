from io import BytesIO

from django_migrations_ci import shell
from django_migrations_ci.exceptions import DumpError


def dump(connection):
    ctx, env = _ctx(connection.settings_dict)
    pg_dump = "pg_dump --no-owner --inserts -h {host} -p {port} -U {user} -d {database}"
    out, err = shell.exec(pg_dump.format(**ctx), env)
    if err:
        raise DumpError(err)

    return BytesIO(out)


def _ctx(db_conf):
    env = {"PGPASSWORD": db_conf["PASSWORD"]}
    try:
        database = db_conf["TEST"]["NAME"] or db_conf["NAME"]
    except KeyError:
        database = db_conf["NAME"]

    data = {
        "host": db_conf["HOST"],
        "port": db_conf["PORT"],
        "user": db_conf["USER"],
        "database": database,
    }
    return data, env
