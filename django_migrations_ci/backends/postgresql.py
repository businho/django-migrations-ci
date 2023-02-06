from django_migrations_ci import shell


def dump(connection, output_file):
    ctx, env = _ctx(connection.settings_dict)
    pg_dump = "pg_dump --no-owner --inserts -h {host} -p {port} -U {user} -d {database} -f {output_file}"  # noqa: E501
    shell.exec(pg_dump.format(output_file=output_file, **ctx), env)


def database_exists(connection, database_name):
    with connection.creation._nodb_cursor() as cursor:
        return connection.creation._database_exists(cursor, database_name)


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
