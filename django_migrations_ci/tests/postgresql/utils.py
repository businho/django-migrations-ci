from contextlib import contextmanager

from django.db import connections


@contextmanager
def _get_cursor():
    # Encapsulate connection because it must close the connection too,
    # because I can't drop database if this connection remains open.
    connection = connections["postgresql"]
    try:
        yield connection.cursor()
    finally:
        connection.close()


def databases():
    with _get_cursor() as cursor:
        cursor.execute("select datname FROM pg_database")
        dbs = {db for db, in cursor.fetchall()}
    return dbs
