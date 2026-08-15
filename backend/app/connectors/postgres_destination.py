
import psycopg2
from app.connectors.base import DestinationConnector


class PostgresDestinationConnector(DestinationConnector):
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

                if write_mode == "upsert":
                    primary_key = self.config.get("primary_key")
                    if not primary_key:
                        raise ValueError("write_mode='upsert' requires 'primary_key' in config")

                    conflict_cols = ", ".join(f'"{c}"' for c in primary_key)
                    update_cols = [c for c in columns if c not in primary_key]

                    if not update_cols:
                        insert_sql = (
                            f'INSERT INTO "{schema}"."{table}" ({col_list}) VALUES ({placeholders}) '
                            f'ON CONFLICT ({conflict_cols}) DO NOTHING'
                        )
                    else:
                        update_clause = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
                        insert_sql = (
                            f'INSERT INTO "{schema}"."{table}" ({col_list}) VALUES ({placeholders}) '
                            f'ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}'
                        )
                else:
                    insert_sql = f'INSERT INTO "{schema}"."{table}" ({col_list}) VALUES ({placeholders})'

                cur.executemany(insert_sql, values)

            conn.commit()
        finally:
            conn.close()