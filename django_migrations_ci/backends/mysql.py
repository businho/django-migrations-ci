from io import BytesIO

from django_migrations_ci import shell
from django_migrations_ci.exceptions import DumpError


def dump(connection):
    ctx, env = _ctx(connection.settings_dict)
    mysqldump = "mysqldump -h {host} -P {port} -u {user} --databases {database}"
    out, err = shell.exec(mysqldump.format(**ctx), env)
    if err:
        raise DumpError(err)

    return BytesIO(out)


def _ctx(db_conf):
    env = {"MYSQL_PWD": db_conf["PASSWORD"]}
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
