"""Oracle backend.

Oracle doesn't have a client tool to dump a schema as SQL, like pg_dump or
mysqldump. The schema DDL comes from DBMS_METADATA and the data from queries.

The dump is a JSON Lines file with one statement per line. Statements with
rows are executed with `executemany`, binding the rows. Binds don't have SQL
literals limits, like 4000 bytes strings, and keep values exact.

Oracle test databases are users (schemas), so the dump and load run connected
as the test user.
"""

import decimal
import json
import re
from contextlib import contextmanager

from django.conf import settings

BATCH_SIZE = 500

# Other object types make the dump fail, instead of caching an incomplete
# database.
SUPPORTED_OBJECT_TYPES = {
    "FUNCTION",
    "INDEX",
    "INDEX PARTITION",
    "INDEX SUBPARTITION",
    "LOB",
    "LOB PARTITION",
    "LOB SUBPARTITION",
    "PACKAGE",
    "PACKAGE BODY",
    "PROCEDURE",
    "SEQUENCE",
    "SYNONYM",
    "TABLE",
    "TABLE PARTITION",
    "TABLE SUBPARTITION",
    "TRIGGER",
    "TYPE",
    "TYPE BODY",
    "VIEW",
}

# PL/SQL object types to DBMS_METADATA object types, specs before bodies.
PLSQL_OBJECT_TYPES = {
    "TYPE": "TYPE_SPEC",
    "PACKAGE": "PACKAGE_SPEC",
    "FUNCTION": "FUNCTION",
    "PROCEDURE": "PROCEDURE",
    "TYPE BODY": "TYPE_BODY",
    "PACKAGE BODY": "PACKAGE_BODY",
}

# Column data types, without precision, to how their values are dumped.
KINDS = {
    "BINARY_DOUBLE": "float",
    "BINARY_FLOAT": "float",
    "BLOB": "blob",
    "BOOLEAN": "boolean",
    "CHAR": "text",
    "CLOB": "clob",
    "DATE": "date",
    "FLOAT": "number",
    "INTERVAL DAY TO SECOND": "interval_ds",
    "INTERVAL YEAR TO MONTH": "interval_ym",
    "JSON": "json",
    "NCHAR": "text",
    "NCLOB": "nclob",
    "NUMBER": "number",
    "NVARCHAR2": "text",
    "RAW": "raw",
    "TIMESTAMP": "timestamp",
    "TIMESTAMP WITH LOCAL TIME ZONE": "timestamp_tz",
    "TIMESTAMP WITH TIME ZONE": "timestamp_tz",
    "VARCHAR2": "text",
}

# Values without an exact Python type are dumped as text and converted back
# when loaded. python-oracledb fetches columns with IS JSON constraints, like
# Django JSONField, as dicts, so text and LOBs are converted to keep the text.
# Intervals are added to zero to normalize the ones stored with mixed signs,
# like python-oracledb binds timedelta(days=-1, seconds=1), because TO_CHAR
# formats them wrong.
SELECT_EXPRESSIONS = {
    "blob": "TO_BLOB({})",
    "clob": "TO_CLOB({})",
    "date": "TO_CHAR({}, 'SYYYY-MM-DD HH24:MI:SS')",
    "interval_ds": "TO_CHAR({} + INTERVAL '0' SECOND)",
    "interval_ym": "TO_CHAR({} + INTERVAL '0' MONTH)",
    "json": "JSON_SERIALIZE({} RETURNING CLOB)",
    "nclob": "TO_NCLOB({})",
    "number": "TO_CHAR({}, 'TM9', 'NLS_NUMERIC_CHARACTERS=''.,''')",
    "text": "{} || ''",
    "timestamp": "TO_CHAR({}, 'SYYYY-MM-DD HH24:MI:SS.FF9')",
    "timestamp_tz": "TO_CHAR({}, 'SYYYY-MM-DD HH24:MI:SS.FF9 TZR')",
}
BIND_EXPRESSIONS = {
    "date": "TO_DATE({}, 'SYYYY-MM-DD HH24:MI:SS')",
    "interval_ds": "TO_DSINTERVAL({})",
    "interval_ym": "TO_YMINTERVAL({})",
    "json": "JSON({})",
    "timestamp": "TO_TIMESTAMP({}, 'SYYYY-MM-DD HH24:MI:SS.FF9')",
    "timestamp_tz": "TO_TIMESTAMP_TZ({}, 'SYYYY-MM-DD HH24:MI:SS.FF9 TZR')",
}
# Bind LOBs as LOBs, to keep empty LOBs different from nulls, and floats as
# BINARY_DOUBLE, because NUMBER can't store NaN and infinity.
INPUT_SIZES = {
    "blob": "DB_TYPE_BLOB",
    "clob": "DB_TYPE_CLOB",
    "float": "DB_TYPE_BINARY_DOUBLE",
    "json": "DB_TYPE_CLOB",
    "nclob": "DB_TYPE_NCLOB",
}
# python-oracledb 26 binds empty LOBs as nulls, so they are created in SQL.
EMPTY_LOB_EXPRESSIONS = {
    "blob": "COALESCE(TO_BLOB({}), EMPTY_BLOB())",
    "clob": "COALESCE(TO_CLOB({}), EMPTY_CLOB())",
    "nclob": "COALESCE(TO_NCLOB({}), TO_NCLOB(EMPTY_CLOB()))",
}

# Nested, IOT overflow and secondary tables are created with their parents.
TABLES = """
    SELECT table_name FROM user_tables
    WHERE nested = 'NO' AND secondary = 'N' AND dropped = 'NO'
      AND (iot_type IS NULL OR iot_type = 'IOT')
"""
# Indexes of primary keys and unique constraints are created with the tables.
INDEXES = f"""
    SELECT index_name FROM user_indexes i
    WHERE index_type NOT IN ('LOB', 'IOT - TOP') AND table_name IN ({TABLES})
      AND NOT EXISTS (
        SELECT 1 FROM user_constraints c
        WHERE c.index_name = i.index_name AND c.constraint_type IN ('P', 'U')
      )
"""
FOREIGN_KEYS = f"""
    SELECT constraint_name FROM user_constraints
    WHERE constraint_type = 'R' AND table_name IN ({TABLES})
"""
COLUMNS = f"""
    SELECT table_name, column_name, data_type FROM user_tab_cols
    WHERE table_name IN ({TABLES})
      AND virtual_column = 'NO' AND user_generated = 'YES'
    ORDER BY table_name, internal_column_id
"""
PRIMARY_KEYS = """
    SELECT c.table_name, cc.column_name FROM user_constraints c
    JOIN user_cons_columns cc ON cc.constraint_name = c.constraint_name
    WHERE c.constraint_type = 'P'
    ORDER BY c.table_name, cc.position
"""
IDENTITY_COLUMNS = """
    SELECT i.table_name, i.column_name, i.generation_type, c.default_on_null
    FROM user_tab_identity_cols i
    JOIN user_tab_cols c
      ON c.table_name = i.table_name AND c.column_name = i.column_name
"""

# DDL of all objects of a type, as statements separated by NUL characters.
# One DBMS_METADATA.GET_DDL call for each object is too slow.
FETCH_DDL = """
DECLARE
    handle NUMBER;
    transform NUMBER;
    ddls sys.ku$_ddls;
BEGIN
    handle := DBMS_METADATA.OPEN(:object_type);
    DBMS_METADATA.SET_FILTER(handle, 'NAME_EXPR', :name_expr);
    DBMS_METADATA.SET_COUNT(handle, 100);
    transform := DBMS_METADATA.ADD_TRANSFORM(handle, 'DDL');
    DBMS_METADATA.SET_TRANSFORM_PARAM(transform, 'PRETTY', FALSE);
    DBMS_METADATA.SET_TRANSFORM_PARAM(transform, 'SQLTERMINATOR', FALSE);
    DBMS_METADATA.SET_TRANSFORM_PARAM(transform, 'EMIT_SCHEMA', FALSE);
    IF :object_type IN ('TABLE', 'INDEX') THEN
        -- Create them in the test user default tablespace.
        DBMS_METADATA.SET_TRANSFORM_PARAM(
            transform, 'SEGMENT_ATTRIBUTES', FALSE
        );
    END IF;
    IF :object_type = 'TABLE' THEN
        -- Foreign keys are created after the data.
        DBMS_METADATA.SET_TRANSFORM_PARAM(transform, 'REF_CONSTRAINTS', FALSE);
    END IF;
    DBMS_LOB.CREATETEMPORARY(:statements, TRUE);
    LOOP
        ddls := DBMS_METADATA.FETCH_DDL(handle);
        EXIT WHEN ddls IS NULL;
        FOR i IN 1 .. ddls.COUNT LOOP
            DBMS_LOB.APPEND(:statements, ddls(i).ddlText);
            DBMS_LOB.WRITEAPPEND(:statements, 1, CHR(0));
        END LOOP;
    END LOOP;
    DBMS_METADATA.CLOSE(handle);
END;
"""

# Objects created before their dependencies are invalid until compiled.
COMPILE_SCHEMA = """
BEGIN
    DBMS_UTILITY.COMPILE_SCHEMA(schema => USER, compile_all => FALSE);
END;
"""


def dump(connection, output_file):
    connection.ensure_connection()
    with connection.connection.cursor() as cursor, open(output_file, "w") as f:
        # Database is python-oracledb, or cx_Oracle in Django<5.
        for entry in _dump(cursor, connection.Database):
            f.write(json.dumps(entry))
            f.write("\n")


def load(connection, content):
    connection.ensure_connection()
    for line in content.split("\n"):
        if not line:
            continue
        entry = json.loads(line)
        with connection.connection.cursor() as cursor:
            if "rows" not in entry:
                cursor.execute(entry["sql"])
                continue
            kinds = entry["binds"]
            input_sizes = (INPUT_SIZES.get(kind) for kind in kinds)
            cursor.setinputsizes(
                *(size and getattr(connection.Database, size) for size in input_sizes)
            )
            cursor.executemany(
                entry["sql"],
                [
                    [
                        _decode(kind, value)
                        for kind, value in zip(kinds, row, strict=True)
                    ]
                    for row in entry["rows"]
                ],
            )


def database_exists(connection, database_name):
    # The test database is the test user, database_name is the service name.
    username = connection.creation._test_database_user().upper()
    with connection.creation._maindb_connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM all_users WHERE username = %s", [username])
        return cursor.fetchone() is not None


@contextmanager
def test_user(connection):
    """Connect as the test user, like Django does when running tests."""
    creation = connection.creation
    user = creation._test_database_user()
    password = creation._test_database_passwd()
    saved = (connection.settings_dict["USER"], connection.settings_dict["PASSWORD"])
    _set_credentials(connection, user, password, saved=saved)
    try:
        yield
    finally:
        _set_credentials(connection, *saved)


def restore_user(connection):
    """Undo Django's switch to the test user, done when creating it.

    Django creates the test user with a random password when TEST["PASSWORD"]
    is not set, so it is saved there to connect again with `test_user`.
    """
    settings_dict = connection.settings_dict
    if "SAVED_USER" not in settings_dict:
        return
    for test_settings in (
        settings_dict["TEST"],
        settings.DATABASES[connection.alias]["TEST"],
    ):
        if test_settings.get("PASSWORD") is None:
            test_settings["PASSWORD"] = settings_dict["PASSWORD"]
    _set_credentials(
        connection,
        settings_dict["SAVED_USER"],
        settings_dict["SAVED_PASSWORD"],
    )


def _set_credentials(connection, user, password, saved=None):
    for settings_dict in (
        connection.settings_dict,
        settings.DATABASES[connection.alias],
    ):
        settings_dict["USER"] = user
        settings_dict["PASSWORD"] = password
        if saved:
            settings_dict["SAVED_USER"], settings_dict["SAVED_PASSWORD"] = saved
        else:
            settings_dict.pop("SAVED_USER", None)
            settings_dict.pop("SAVED_PASSWORD", None)
    connection.close()


def _dump(cursor, database):
    _check_object_types(cursor)

    def ddl(object_type, names):
        return _fetch_ddl(cursor, database, object_type, names)

    yield from ddl(
        "SEQUENCE",
        "SELECT object_name FROM user_objects "
        "WHERE object_type = 'SEQUENCE' AND generated = 'N'",
    )
    yield from ddl("TABLE", TABLES)

    # Like pg_dump, load the data before creating indexes and foreign keys,
    # so rows are inserted in any order and indexes are built once.
    primary_keys = _group_by_table(cursor, PRIMARY_KEYS)
    identity_columns = _group_by_table(cursor, IDENTITY_COLUMNS)
    for table, columns in _group_by_table(cursor, COLUMNS).items():
        yield from _dump_rows(
            cursor,
            table,
            columns,
            [column for (column,) in primary_keys.get(table, [])],
            identity_columns.get(table, []),
        )

    yield from ddl("SYNONYM", "SELECT synonym_name FROM user_synonyms")
    compiled = []
    for object_type, metadata_object_type in PLSQL_OBJECT_TYPES.items():
        compiled += ddl(
            metadata_object_type,
            "SELECT object_name FROM user_objects "
            f"WHERE object_type = '{object_type}' AND generated = 'N'",
        )
    compiled += ddl("VIEW", "SELECT view_name FROM user_views")
    yield from compiled
    yield from ddl("INDEX", INDEXES)
    yield from ddl("REF_CONSTRAINT", FOREIGN_KEYS)
    # Triggers are created after the data, so they don't fire while loading.
    triggers = ddl(
        "TRIGGER",
        "SELECT trigger_name FROM user_triggers WHERE trigger_name NOT LIKE 'BIN$%'",
    )
    yield from triggers
    yield from _dump_comments(cursor)
    if compiled or triggers:
        yield {"sql": COMPILE_SCHEMA}


def _dump_rows(cursor, table, columns, primary_key, identity_columns):
    kinds = [_column_kind(table, column, data_type) for column, data_type in columns]
    select_list = ", ".join(
        SELECT_EXPRESSIONS.get(kind, "{}").format(f'"{column}"')
        for (column, _), kind in zip(columns, kinds, strict=True)
    )
    query = f'SELECT {select_list} FROM "{table}"'
    if primary_key:
        query += " ORDER BY " + ", ".join(f'"{column}"' for column in primary_key)

    column_list = ", ".join(f'"{column}"' for column, _ in columns)

    def insert(empty_lobs):
        binds = []
        for position, kind in enumerate(kinds, start=1):
            if position in empty_lobs:
                expression = EMPTY_LOB_EXPRESSIONS[kind]
            else:
                expression = BIND_EXPRESSIONS.get(kind, "{}")
            binds.append(expression.format(f":{position}"))
        return f'INSERT INTO "{table}" ({column_list}) VALUES ({", ".join(binds)})'

    with cursor.connection.cursor() as data_cursor:
        data_cursor.arraysize = BATCH_SIZE
        data_cursor.execute(query)
        rows = data_cursor.fetchmany()
        if not rows:
            return

        for column, generation_type, _ in identity_columns:
            if generation_type == "ALWAYS":
                yield {
                    "sql": f'ALTER TABLE "{table}" MODIFY '
                    f'("{column}" GENERATED BY DEFAULT AS IDENTITY)'
                }

        while rows:
            # Rows with empty LOBs are inserted apart, to create the empty LOBs.
            batches = {}
            for row in rows:
                values = [
                    _encode(kind, value) for kind, value in zip(kinds, row, strict=True)
                ]
                empty_lobs = tuple(
                    position
                    for position, (kind, value) in enumerate(
                        zip(kinds, values, strict=True), 1
                    )
                    if kind in EMPTY_LOB_EXPRESSIONS and value == ""
                )
                batches.setdefault(empty_lobs, []).append(values)
            for empty_lobs, batch in batches.items():
                yield {"sql": insert(empty_lobs), "binds": kinds, "rows": batch}
            rows = data_cursor.fetchmany()

    # Continue identities after the loaded rows.
    for column, generation_type, default_on_null in identity_columns:
        on_null = " ON NULL" if default_on_null == "YES" else ""
        yield {
            "sql": f'ALTER TABLE "{table}" MODIFY ("{column}" '
            f"GENERATED {generation_type}{on_null} AS IDENTITY "
            "(START WITH LIMIT VALUE))"
        }


def _dump_comments(cursor):
    names = f"{TABLES} UNION SELECT view_name FROM user_views"
    for name, comment in _rows(
        cursor,
        "SELECT table_name, comments FROM user_tab_comments "
        f"WHERE comments IS NOT NULL AND table_name IN ({names}) "
        "ORDER BY table_name",
    ):
        yield {"sql": f'COMMENT ON TABLE "{name}" IS {_literal(comment)}'}

    for name, column, comment in _rows(
        cursor,
        "SELECT table_name, column_name, comments FROM user_col_comments "
        f"WHERE comments IS NOT NULL AND table_name IN ({names}) "
        "ORDER BY table_name, column_name",
    ):
        yield {"sql": f'COMMENT ON COLUMN "{name}"."{column}" IS {_literal(comment)}'}


def _check_object_types(cursor):
    unsupported = [
        f"{object_type} {name}"
        for object_type, name in _rows(
            cursor,
            "SELECT object_type, object_name FROM user_objects "
            "WHERE object_name NOT LIKE 'BIN$%' ORDER BY object_type, object_name",
        )
        if object_type not in SUPPORTED_OBJECT_TYPES
    ]
    if unsupported:
        msg = f"Can't dump Oracle objects: {', '.join(unsupported)}."
        raise NotImplementedError(msg)


def _column_kind(table, column, data_type):
    # Remove precisions, e.g. TIMESTAMP(6) WITH TIME ZONE.
    kind = KINDS.get(re.sub(r"\(\d+\)", "", data_type))
    if kind is None:
        msg = f"Can't dump Oracle {data_type} column {table}.{column}."
        raise NotImplementedError(msg)
    return kind


def _encode(kind, value):
    if hasattr(value, "read"):
        value = value.read()
    if value is None:
        return None
    if kind in ("blob", "raw"):
        return value.hex()
    if kind == "number" and re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _decode(kind, value):
    if value is None:
        return None
    if kind in ("blob", "raw"):
        return bytes.fromhex(value)
    if kind == "number" and isinstance(value, str):
        return decimal.Decimal(value)
    return value


def _fetch_ddl(cursor, database, object_type, names):
    statements = cursor.var(database.DB_TYPE_CLOB)
    cursor.execute(
        FETCH_DDL,
        object_type=object_type,
        name_expr=f"IN ({names})",
        statements=statements,
    )
    return [
        {"sql": statement.strip()}
        for statement in statements.getvalue().read().split("\0")[:-1]
    ]


def _group_by_table(cursor, query):
    groups = {}
    for table, *values in _rows(cursor, query):
        groups.setdefault(table, []).append(values)
    return groups


def _rows(cursor, query):
    cursor.execute(query)
    return cursor.fetchall()


def _literal(value):
    return "'{}'".format(value.replace("'", "''"))
