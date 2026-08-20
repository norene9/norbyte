
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

    def ensure_table_matches_schema(self, table: str, source_columns: list[dict]) -> None:
        """Create a missing destination table using the source PostgreSQL types."""
        if not source_columns:
            raise ValueError(f"No schema metadata found for source table '{table}'")

        schema = self.config.get("schema", "public")
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

        create_table = sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
            sql.Identifier(schema),
            sql.Identifier(table),
            sql.SQL(", ").join(column_definitions),
        )

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(create_table)
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