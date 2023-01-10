from io import StringIO


def dump(connection):
    connection.ensure_connection()
    sql = "".join(f"{sql}\n" for sql in connection.connection.iterdump())
    return StringIO(sql)
