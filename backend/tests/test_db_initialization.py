import os
import sys
import unittest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import initialize_database


class DatabaseInitializationTests(unittest.TestCase):
    def test_initialize_database_creates_expected_tables(self):
        engine = create_engine("sqlite:///:memory:")

        initialize_database(engine)

        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'projects', 'connection')")
            )
            table_names = {row[0] for row in result.fetchall()}

        self.assertTrue({"users", "projects", "connection"}.issubset(table_names))


if __name__ == "__main__":
    unittest.main()
