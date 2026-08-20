import psycopg2
import psycopg2.extras
from typing import Iterator
from app.connectors.base import SourceConnector
import re


class PostgresSourceConnector(SourceConnector):
    def _connect(self):
        return psycopg2.connect(
            host=self.config["host"],
            port=self.config["port"],
            dbname=self.config["database"],
            user=self.config["username"],
            password=self.config["password"],
            sslmode="require" if self.config.get("ssl") else "prefer",
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

    def get_table_schema(self, table: str) -> list[dict]:
        """Return the source table's column definitions from PostgreSQL metadata."""
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
            return [
                {
                    "name": column[0],
                    "data_type": column[1],
                    "max_length": column[2],
                    "nullable": column[3] == "YES",
                }
                for column in columns
            ]
        finally:
            conn.close()

    def read_records(self, table: str, cursor_field: str | None = None, cursor_value: str | None = None) -> Iterator[dict]:
        schema = self.config.get("schema", "public")
        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if cursor_field and cursor_value is not None:
                    # Basic validation for column identifier to avoid SQL injection via column name
                    if not re.match(r"^[A-Za-z0-9_]+$", cursor_field):
                        raise ValueError("Invalid cursor_field")
                    # Use a parameterized query to avoid SQL injection
                    query = f'SELECT * FROM "{schema}"."{table}" WHERE "{cursor_field}" > %s ORDER BY "{cursor_field}" ASC'
                    cur.execute(query, (cursor_value,))
                else:
                    cur.execute(f'SELECT * FROM "{schema}"."{table}"')
                for row in cur:
                    yield dict(row)
        finally:
            conn.close()