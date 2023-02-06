from django.db.backends.utils import strip_quotes

from django_migrations_ci import shell


def dump(connection, output_file):
    ctx, env = _ctx(connection.settings_dict)
    mysqldump = "mysqldump -h {host} -P {port} -u {user} --databases {database} --result-file {output_file}"  # noqa: E501
    shell.exec(mysqldump.format(output_file=output_file, **ctx), env)


def database_exists(connection, database_name):
    with connection.creation._nodb_cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            [strip_quotes(database_name)],
        )
        return cursor.fetchone() is not None


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
