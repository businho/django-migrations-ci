def dump(connection, output_file):
    connection.ensure_connection()
    sql = "".join(f"{sql}\n" for sql in connection.connection.iterdump())
    with open(output_file, "w") as f:
        f.write(sql)
