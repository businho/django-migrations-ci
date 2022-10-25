import sqlite3

from django.conf import settings


def load(alias, input_file):
    db_conf = settings.DATABASES[alias]
    db_name = db_conf["TEST"]["NAME"]

    with sqlite3.connect(db_name) as conn:
        with open(input_file, "r") as f:
            conn.executescript(f.read())


def dump(alias, output_file):
    db_conf = settings.DATABASES[alias]
    db_name = db_conf["TEST"]["NAME"]

    with sqlite3.connect(db_name) as conn:
        with open(output_file, "w") as f:
            f.writelines(f"{sql}\n" for sql in conn.iterdump())
