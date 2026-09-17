
import json
import math
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from psycopg2.extras import Json
from app.connectors.base import DestinationConnector


PYTHON_TO_PG_TYPE = {
    int: "BIGINT",
    float: "DOUBLE PRECISION",
    bool: "BOOLEAN",
    str: "TEXT",
    dict: "JSONB",
    list: "JSONB",
}


class PostgresDestinationConnector(DestinationConnector):
    def _connect(self):
        connection_options = {
            "host": self.config["host"],
            "port": self.config["port"],
            "dbname": self.config["database"],
            "user": self.config["username"],
            "password": self.config["password"],
            "sslmode": "require" if self.config.get("ssl") else "prefer",
        }
        if self.config.get("connect_timeout") is not None:
            connection_options["connect_timeout"] = self.config["connect_timeout"]

        return psycopg2.connect(
            **connection_options,
        )

    def test_connection(self) -> bool:
        conn = self._connect()
        conn.close()
        return True

    def _serialize_value(self, value):
        """Serialize Python values for PostgreSQL, wrapping dict/list in Json()."""
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, (dict, list)):
            return Json(value)
        return value

    def _resolve_pg_type(self, seen_types: set) -> str:
        """Resolve PostgreSQL type from a set of Python types seen in a column."""
        if not seen_types:
            return "TEXT"
        if len(seen_types) > 1:
            return "TEXT"
        py_type = next(iter(seen_types))
        return PYTHON_TO_PG_TYPE.get(py_type, "TEXT")

    def _infer_schema(self, records: list[dict]) -> dict:
        """Infer PostgreSQL column types by sampling records."""
        column_types = {}
        
        for record in records:
            for key, value in record.items():
                if key not in column_types:
                    column_types[key] = set()
                
                if value is not None:
                    column_types[key].add(type(value))
        
        # Convert sets of types to single resolved type
        return {col: self._resolve_pg_type(types) for col, types in column_types.items()}

    def _ensure_table_exists(self, cur, schema: str, table: str, column_types: dict) -> None:
        """Create or alter table to match inferred schema."""
        # First, check if table exists
        cur.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            )
            """,
            (schema, table),
        )
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            # Create table if it doesn't exist
            column_defs = []
            for col, pg_type in column_types.items():
                column_defs.append(sql.SQL("{} {}").format(
                    sql.Identifier(col),
                    sql.SQL(pg_type)
                ))
            
            create_table_sql = sql.SQL("CREATE TABLE {}.{} ({})").format(
                sql.Identifier(schema),
                sql.Identifier(table),
                sql.SQL(", ").join(column_defs)
            )
            cur.execute(create_table_sql)
        else:
            # Table exists - check and update column types if needed
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                """,
                (schema, table),
            )
            existing_cols = {row[0]: row[1] for row in cur.fetchall()}
            
            # Add missing columns or alter types if needed
            for col, pg_type in column_types.items():
                if col not in existing_cols:
                    # Add missing column
                    cur.execute(
                        sql.SQL("ALTER TABLE {}.{} ADD COLUMN {} {}").format(
                            sql.Identifier(schema),
                            sql.Identifier(table),
                            sql.Identifier(col),
                            sql.SQL(pg_type)
                        )
                    )
                elif existing_cols[col].upper() != pg_type.upper():
                    # Column type mismatch - alter to the inferred type
                    # Use USING to convert (e.g., TEXT to JSONB)
                    if pg_type == "JSONB" and existing_cols[col].upper() in ("TEXT", "VARCHAR", "CHARACTER VARYING"):
                        # Safe conversion from TEXT to JSONB
                        cur.execute(
                            sql.SQL("ALTER TABLE {}.{} ALTER COLUMN {} TYPE {} USING {}::{}").format(
                                sql.Identifier(schema),
                                sql.Identifier(table),
                                sql.Identifier(col),
                                sql.SQL("JSONB"),
                                sql.Identifier(col),
                                sql.SQL("JSONB")
                            )
                        )

    def discover(self) -> list[str]:
        schema = self.config.get("schema", "public")
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                    (schema,),
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_table_schema(self, table: str) -> list[dict]:
        """Return destination table columns and primary-key metadata."""
        schema = self.config.get("schema", "public")
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name, data_type, character_maximum_length, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (schema, table),
                )
                columns = cur.fetchall()
                cur.execute(
                    """
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.table_schema = kcu.table_schema
                     AND tc.table_name = kcu.table_name
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                      AND tc.table_schema = %s
                      AND tc.table_name = %s
                    ORDER BY kcu.ordinal_position
                    """,
                    (schema, table),
                )
                primary_key_columns = {row[0] for row in cur.fetchall()}
            return [
                {
                    "name": column[0],
                    "data_type": column[1],
                    "max_length": column[2],
                    "nullable": column[3] == "YES",
                    "primary_key": column[0] in primary_key_columns,
                }
                for column in columns
            ]
        finally:
            conn.close()

    def truncate_table(self, table: str, table_prefix: str = "") -> None:
        schema = self.config.get("schema", "public")
        actual_table = f"{table_prefix}{table}"
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("TRUNCATE TABLE {}.{}").format(
                        sql.Identifier(schema),
                        sql.Identifier(actual_table),
                    )
                )
            conn.commit()
        finally:
            conn.close()

    def drop_table(self, table: str, table_prefix: str = "") -> None:
        schema = self.config.get("schema", "public")
        actual_table = f"{table_prefix}{table}"
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                        sql.Identifier(schema),
                        sql.Identifier(actual_table),
                    )
                )
            conn.commit()
        finally:
            conn.close()

    def ensure_table_matches_schema(self, table: str, source_columns: list[dict], table_prefix: str = "") -> None:
        """Make the destination table's columns match the source schema."""
        if not source_columns:
            raise ValueError(f"No schema metadata found for source table '{table}'")

        schema = self.config.get("schema", "public")
        actual_table = f"{table_prefix}{table}"
        configured_primary_key = self.config.get("primary_key", [])
        if isinstance(configured_primary_key, str):
            configured_primary_key = [configured_primary_key]
        primary_key = configured_primary_key or [
            column["name"] for column in source_columns if column.get("primary_key")
        ]
        column_definitions = []
        for column in source_columns:
            pg_type = column["data_type"]
            if column.get("max_length"):
                pg_type = f"{pg_type}({column['max_length']})"

            definition = sql.SQL("{} {}{}").format(
                sql.Identifier(column["name"]),
                sql.SQL(pg_type),
                sql.SQL("") if column.get("nullable", True) else sql.SQL(" NOT NULL"),
            )
            column_definitions.append(definition)

        if primary_key:
            primary_key_sql = sql.SQL(", ").join(sql.Identifier(column) for column in primary_key)
            column_definitions.append(sql.SQL("PRIMARY KEY ({})").format(primary_key_sql))

        create_table = sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
            sql.Identifier(schema),
            sql.Identifier(actual_table),
            sql.SQL(", ").join(column_definitions),
        )

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    (schema, actual_table),
                )
                existing_columns = {row[0] for row in cur.fetchall()}

                cur.execute(
                                        """
                                        SELECT tc.constraint_name, kcu.column_name
                                        FROM information_schema.table_constraints AS tc
                                        JOIN information_schema.key_column_usage AS kcu
                                            ON tc.constraint_name = kcu.constraint_name
                                         AND tc.table_schema = kcu.table_schema
                                         AND tc.table_name = kcu.table_name
                                        WHERE tc.constraint_type = 'PRIMARY KEY'
                                            AND tc.table_schema = %s
                                            AND tc.table_name = %s
                                        ORDER BY kcu.ordinal_position
                                        """,
                                        (schema, actual_table),
                                )
                primary_key_rows = cur.fetchall()

                if not existing_columns:
                    cur.execute(create_table)
                else:
                    source_column_names = {column["name"] for column in source_columns}

                    cur.execute(
                        """
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        """,
                        (schema, actual_table),
                    )
                    existing_column_types = {row[0]: row[1] for row in cur.fetchall()}

                    for column in source_columns:
                        pg_type = column["data_type"]
                        if column.get("max_length"):
                            pg_type = f"{pg_type}({column['max_length']})"

                        if column["name"] not in existing_columns:
                            nullable = "" if column.get("nullable", True) else " NOT NULL"
                            cur.execute(
                                sql.SQL("ALTER TABLE {}.{} ADD COLUMN {} {}{}")
                                .format(
                                    sql.Identifier(schema),
                                    sql.Identifier(actual_table),
                                    sql.Identifier(column["name"]),
                                    sql.SQL(pg_type),
                                    sql.SQL(nullable),
                                )
                            )
                        elif existing_column_types[column["name"]].upper() != column["data_type"].upper():
                            # Type drifted from source (e.g. an older integer column that must widen to bigint)
                            cur.execute(
                                sql.SQL("ALTER TABLE {}.{} ALTER COLUMN {} TYPE {} USING {}::{}")
                                .format(
                                    sql.Identifier(schema),
                                    sql.Identifier(actual_table),
                                    sql.Identifier(column["name"]),
                                    sql.SQL(pg_type),
                                    sql.Identifier(column["name"]),
                                    sql.SQL(pg_type),
                                )
                            )

                    for column_name in existing_columns - source_column_names:
                        cur.execute(
                            sql.SQL("ALTER TABLE {}.{} DROP COLUMN {}")
                            .format(
                                sql.Identifier(schema),
                                sql.Identifier(actual_table),
                                sql.Identifier(column_name),
                            )
                        )

                    existing_primary_key = [row[1] for row in primary_key_rows]
                    if primary_key and existing_primary_key != primary_key:
                        if existing_primary_key:
                            cur.execute(
                                sql.SQL("ALTER TABLE {}.{} DROP CONSTRAINT {}")
                                .format(
                                    sql.Identifier(schema),
                                    sql.Identifier(actual_table),
                                    sql.Identifier(primary_key_rows[0][0]),
                                )
                            )
                        cur.execute(
                            sql.SQL("ALTER TABLE {}.{} ADD CONSTRAINT {} PRIMARY KEY ({})")
                            .format(
                                sql.Identifier(schema),
                                sql.Identifier(actual_table),
                                sql.Identifier(f"{actual_table}_pkey"),
                                sql.SQL(", ").join(sql.Identifier(column) for column in primary_key),
                            )
                        )
            conn.commit()
        finally:
            conn.close()

    def read_records(self, table: str, limit: int = 50, table_prefix: str = "") -> list[dict]:
        schema = self.config.get("schema", "public")
        actual_table = f"{table_prefix}{table}"
        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f'SELECT * FROM "{schema}"."{actual_table}" LIMIT %s', (limit,))
                return [
                    {key: (None if isinstance(value, float) and not math.isfinite(value) else value) for key, value in row.items()}
                    for row in cur.fetchall()
                ]
        finally:
            conn.close()

    def write_records(self, table: str, records: list[dict], table_prefix: str = "") -> None:
        if not records:
            return

        schema = self.config.get("schema", "public")
        actual_table = f"{table_prefix}{table}"
        write_mode = self.config.get("write_mode", "append")
        
        # Infer schema from records
        column_types = self._infer_schema(records)
        columns = list(column_types.keys())

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                self._ensure_table_exists(cur, schema, actual_table, column_types)

                if write_mode == "overwrite":
                    cur.execute(f'TRUNCATE TABLE "{schema}"."{actual_table}"')

                col_list = ", ".join(f'"{c}"' for c in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                # Serialize dict/list values via psycopg2's Json() adapter
                values = [
                    tuple(self._serialize_value(record.get(c)) for c in columns)
                    for record in records
                ]

                if write_mode == "upsert":
                    primary_key = self.config.get("primary_key")
                    if not primary_key:
                        raise ValueError("write_mode='upsert' requires 'primary_key' in config")

                    conflict_cols = ", ".join(f'"{c}"' for c in primary_key)
                    update_cols = [c for c in columns if c not in primary_key]

                    if not update_cols:
                        insert_sql = (
                            f'INSERT INTO "{schema}"."{actual_table}" ({col_list}) VALUES %s '
                            f'ON CONFLICT ({conflict_cols}) DO NOTHING'
                        )
                    else:
                        update_clause = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
                        insert_sql = (
                            f'INSERT INTO "{schema}"."{actual_table}" ({col_list}) VALUES %s '
                            f'ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}'
                        )
                else:
                    insert_sql = f'INSERT INTO "{schema}"."{actual_table}" ({col_list}) VALUES %s'

                page_size = self.config.get("write_batch_size", 1000)
                psycopg2.extras.execute_values(
                    cur,
                    insert_sql,
                    values,
                    template=f"({placeholders})",
                    page_size=page_size,
                )

            conn.commit()
        finally:
            conn.close()