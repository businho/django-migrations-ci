from contextlib import contextmanager

import psycopg2
from django.conf import settings


@contextmanager
def _get_cursor():
    db_conf = settings.DATABASES["postgresql"]
    conn = psycopg2.connect(
        "postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}".format(**db_conf)
    )
    try:
        with conn:
            yield conn.cursor()
    finally:
        conn.close()


def databases():
    with _get_cursor() as cursor:
        cursor.execute("select datname FROM pg_database")
        dbs = {db for db, in cursor.fetchall()}
    return dbs
