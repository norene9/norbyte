import psycopg2
import psycopg2.extras
from typing import Iterator
from app.connectors.base import SourceConnector


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

    def read_records(self, table: str) -> Iterator[dict]:
        schema = self.config.get("schema", "public")
        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f'SELECT * FROM "{schema}"."{table}"')
                for row in cur:
                    yield dict(row)
        finally:
            conn.close()