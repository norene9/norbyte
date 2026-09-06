
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from app.connectors.base import DestinationConnector


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

    def truncate_table(self, table: str) -> None:
        schema = self.config.get("schema", "public")
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("TRUNCATE TABLE {}.{}").format(
                        sql.Identifier(schema),
                        sql.Identifier(table),
                    )
                )
            conn.commit()
        finally:
            conn.close()

    def ensure_table_matches_schema(self, table: str, source_columns: list[dict]) -> None:
        """Make the destination table's columns match the source schema."""
        if not source_columns:
            raise ValueError(f"No schema metadata found for source table '{table}'")

        schema = self.config.get("schema", "public")
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
            sql.Identifier(table),
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
                    (schema, table),
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
                                        (schema, table),
                                )
                primary_key_rows = cur.fetchall()

                if not existing_columns:
                    cur.execute(create_table)
                else:
                    source_column_names = {column["name"] for column in source_columns}

                    for column in source_columns:
                        if column["name"] in existing_columns:
                            continue

                        pg_type = column["data_type"]
                        if column.get("max_length"):
                            pg_type = f"{pg_type}({column['max_length']})"
                        nullable = "" if column.get("nullable", True) else " NOT NULL"
                        cur.execute(
                            sql.SQL("ALTER TABLE {}.{} ADD COLUMN {} {}{}")
                            .format(
                                sql.Identifier(schema),
                                sql.Identifier(table),
                                sql.Identifier(column["name"]),
                                sql.SQL(pg_type),
                                sql.SQL(nullable),
                            )
                        )

                    for column_name in existing_columns - source_column_names:
                        cur.execute(
                            sql.SQL("ALTER TABLE {}.{} DROP COLUMN {}")
                            .format(
                                sql.Identifier(schema),
                                sql.Identifier(table),
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
                                    sql.Identifier(table),
                                    sql.Identifier(primary_key_rows[0][0]),
                                )
                            )
                        cur.execute(
                            sql.SQL("ALTER TABLE {}.{} ADD CONSTRAINT {} PRIMARY KEY ({})")
                            .format(
                                sql.Identifier(schema),
                                sql.Identifier(table),
                                sql.Identifier(f"{table}_pkey"),
                                sql.SQL(", ").join(sql.Identifier(column) for column in primary_key),
                            )
                        )
            conn.commit()
        finally:
            conn.close()

    def read_records(self, table: str, limit: int = 50) -> list[dict]:
        schema = self.config.get("schema", "public")
        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT %s', (limit,))
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def write_records(self, table: str, records: list[dict]) -> None:
        if not records:
            return

        schema = self.config.get("schema", "public")
        write_mode = self.config.get("write_mode", "append")
        columns = list(records[0].keys())

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                if write_mode == "overwrite":
                    cur.execute(f'TRUNCATE TABLE "{schema}"."{table}"')

                col_list = ", ".join(f'"{c}"' for c in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                values = [tuple(record[c] for c in columns) for record in records]
                values_placeholder = "%s"

                if write_mode == "upsert":
                    primary_key = self.config.get("primary_key")
                    if not primary_key:
                        raise ValueError("write_mode='upsert' requires 'primary_key' in config")

                    conflict_cols = ", ".join(f'"{c}"' for c in primary_key)
                    update_cols = [c for c in columns if c not in primary_key]

                    if not update_cols:
                        insert_sql = (
                            f'INSERT INTO "{schema}"."{table}" ({col_list}) VALUES {values_placeholder} '
                            f'ON CONFLICT ({conflict_cols}) DO NOTHING'
                        )
                    else:
                        update_clause = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
                        insert_sql = (
                            f'INSERT INTO "{schema}"."{table}" ({col_list}) VALUES {values_placeholder} '
                            f'ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}'
                        )
                else:
                    insert_sql = f'INSERT INTO "{schema}"."{table}" ({col_list}) VALUES {values_placeholder}'

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