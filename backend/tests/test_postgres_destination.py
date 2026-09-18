import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.connectors.postgres_destination import PostgresDestinationConnector


class FakeCursor:
    def __init__(self, existing_columns, primary_key_columns=None):
        self.existing_columns = existing_columns
        self.primary_key_columns = primary_key_columns or []
        self.fetchall_count = 0
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        self.queries.append((query, params))

    def fetchall(self):
        self.fetchall_count += 1
        if self.fetchall_count == 1:
            return [(column,) for column in self.existing_columns]
        return [("customers_pkey", column) for column in self.primary_key_columns]


class FakeConnection:
    encoding = "UTF8"

    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def close(self):
        pass

    def escape_identifier(self, value):
        return '"' + value.replace('"', '""') + '"'


class PostgresDestinationSchemaTests(unittest.TestCase):
    def setUp(self):
        self.connector = PostgresDestinationConnector({"schema": "public"})

    def test_adds_new_source_columns(self):
        cursor = FakeCursor(["id", "name"])
        connection = FakeConnection(cursor)

        with patch.object(self.connector, "_connect", return_value=connection):
            self.connector.ensure_table_matches_schema(
                "customers",
                [
                    {"name": "id", "data_type": "integer", "nullable": False},
                    {"name": "name", "data_type": "text", "nullable": True},
                    {"name": "email", "data_type": "text", "nullable": True},
                ],
            )

        self.assertEqual(len(cursor.queries), 3)
        add_query = repr(cursor.queries[2][0])
        self.assertIn("ADD COLUMN", add_query)
        self.assertIn("email", add_query)
        self.assertTrue(connection.committed)

    def test_drops_columns_removed_from_source(self):
        cursor = FakeCursor(["id", "name", "legacy_email"])
        connection = FakeConnection(cursor)

        with patch.object(self.connector, "_connect", return_value=connection):
            self.connector.ensure_table_matches_schema(
                "customers",
                [
                    {"name": "id", "data_type": "integer", "nullable": False},
                    {"name": "name", "data_type": "text", "nullable": True},
                ],
            )

        self.assertEqual(len(cursor.queries), 3)
        drop_query = repr(cursor.queries[2][0])
        self.assertIn("DROP COLUMN", drop_query)
        self.assertIn("legacy_email", drop_query)
        self.assertTrue(connection.committed)


if __name__ == "__main__":
    unittest.main()