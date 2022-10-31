def dump(connection, output_file):
    connection.ensure_connection()
    sql = "".join(f"{sql}\n" for sql in connection.connection.iterdump())

    db_name = connection.settings_dict["NAME"]
    print(f"Dump {db_name} SQL to {output_file}")
    with open(output_file, "w") as f:
        f.write(sql)
