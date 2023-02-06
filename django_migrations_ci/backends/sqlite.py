import os


def dump(connection, output_file):
    connection.ensure_connection()
    sql = "".join(f"{sql}\n" for sql in connection.connection.iterdump())
    with open(output_file, "w") as f:
        f.write(sql)


def database_exists(connection, database_name):
    return os.access(database_name, os.F_OK)
