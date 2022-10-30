import sqlite3


def load(connection, input_file):
    db_name = connection.settings_dict["TEST"]["NAME"]

    print(f"Connecting to sqlite3 {db_name}.")
    with open(input_file, "r") as f:
        sql = f.read()
        print(f"Load SQL to {db_name}")

        with sqlite3.connect(db_name) as conn:
            conn.executescript(sql)


def dump(connection, output_file):
    db_name = connection.settings_dict["TEST"]["NAME"]

    print(f"Connecting to sqlite3 {db_name}.")
    with sqlite3.connect(db_name) as conn:
        sql = "".join(f"{sql}\n" for sql in conn.iterdump())
        print(f"Dump SQL to {db_name}")

        with open(output_file, "w") as f:
            f.write(sql)
