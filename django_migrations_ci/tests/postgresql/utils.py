from contextlib import contextmanager

from django.db import connections


@contextmanager
def _get_cursor(database):
    # Encapsulate connection because it must close the connection too,
    # because I can't drop database if this connection remains open.
    connection = connections[database]
    try:
        yield connection.cursor()
    finally:
        connection.close()


def databases(database="default"):
    with _get_cursor(database) as cursor:
        cursor.execute("select datname FROM pg_database")
        dbs = {db for db, in cursor.fetchall()}
    return dbs
