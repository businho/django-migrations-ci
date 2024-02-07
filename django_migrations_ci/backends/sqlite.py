import os

from django_migrations_ci import shell


def dump(connection, output_file):
    database = connection.settings_dict["NAME"]
    stdout = shell.exec(f"sqlite3 {database} .dump")
    with open(output_file, "wb") as f:
        f.write(stdout)


def database_exists(connection, database_name):
    return os.access(database_name, os.F_OK)
