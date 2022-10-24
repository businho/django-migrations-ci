import sqlite3


def load(db_name, input_file):
    with sqlite3.connect(db_name) as conn:
        with open(input_file, "r") as f:
            conn.executescript(f.read())


def dump(db_name, output_file):
    with sqlite3.connect(db_name) as conn:
        with open(output_file, "w") as f:
            f.writelines(f"{sql}\n" for sql in conn.iterdump())
