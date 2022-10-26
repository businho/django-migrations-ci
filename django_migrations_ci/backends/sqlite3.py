import sqlite3

from django.conf import settings


def load(alias, input_file):
    db_conf = settings.DATABASES[alias]
    db_name = db_conf["TEST"]["NAME"]

    print(f"Connecting to sqlite3 {db_name}.")
    with sqlite3.connect(db_name) as conn:
        with open(input_file, "r") as f:
            sql = f.read()
            print(f"Load SQL to {db_name}: {sql}")
            conn.executescript(sql)


def dump(alias, output_file):
    db_conf = settings.DATABASES[alias]
    db_name = db_conf["TEST"]["NAME"]

    print(f"Connecting to sqlite3 {db_name}.")
    with sqlite3.connect(db_name) as conn:
        with open(output_file, "w") as f:
            sql = f.writelines()
            print(f"Dump SQL to {db_name}: {sql}")
            f.writelines(sql)
