from subprocess import PIPE, Popen


def dump(connection, output_file):
    """
    pg_dump -Fp -h $DB_HOST -U $POSTGRES_USER test_foo -f migrateci-postgresql
    """
    ctx, env = _ctx(connection.settings_dict)
    pg_dump = "pg_dump --no-owner --inserts -h {host} -p {port} -U {user} -d {database} -f {output_file}"  # noqa: E501
    breakpoint()
    _exec(pg_dump.format(output_file=output_file, **ctx), env)


def _exec(command, env):
    if "test_test" in command:
        raise Exception(command)

    print("EXEC", command)
    p = Popen(
        command,
        shell=True,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        env=env,
    )
    stdout, stderr = p.communicate()

    if stderr:
        print("EXEC ERROR", command, stdout, stderr)
    return stdout, stderr


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
