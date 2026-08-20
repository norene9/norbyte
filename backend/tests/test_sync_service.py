import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.encryption import encrypt_config
from app.db.base_class import Base
from app.models import Connection, DestinationDefinition, Project, SourceDefinition, SyncJob, User
from app.repositories.connection_repository import ConnectionRepository
from app.services.definition_service import DefinitionService
from app.services.sync_service import SyncService
from app.repositories.definition_repository import DefinitionRepository


class SyncServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.session = self.Session()

        self.user = User(username="alice", email="alice@example.com", password="secret")
        self.session.add(self.user)
        self.session.commit()

        self.source_def = SourceDefinition(name="Stripe", connector_type="postgres")
        self.destination_def = DestinationDefinition(name="Postgres", connector_type="postgres")
        self.project = Project(name="Demo Project", user_id=self.user.id)
        self.session.add_all([self.source_def, self.destination_def, self.project])
        self.session.commit()

        self.connection = Connection(
            source_id=self.source_def.id,
            destination_id=self.destination_def.id,
            project_id=self.project.id,
            schedule="0 * * * *",
            source_connection_json=encrypt_config({"host": "src", "port": 5432, "database": "app", "username": "u", "password": "p"}),
            destination_connection_json=encrypt_config({"host": "dst", "port": 5432, "database": "app", "username": "u", "password": "p"}),
        )
        self.session.add(self.connection)
        self.session.commit()

        self.service = SyncService(
            self.session,
            ConnectionRepository(self.session),
            DefinitionService(DefinitionRepository(self.session)),
        )

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_run_sync_tracks_successful_job(self):
        source = MagicMock()
        source.discover.return_value = ["customers"]
        source.read_records.return_value = [{"id": 1, "email": "a@example.com"}]

        destination = MagicMock()

        with patch("app.services.sync_service.get_source_connector") as mock_source_connector, patch("app.services.sync_service.get_destination_connector") as mock_destination_connector:
            mock_source_connector.return_value.return_value = source
            mock_destination_connector.return_value.return_value = destination

            job = self.service.run_sync(self.connection.id)

        self.assertEqual(job.status, "success")
        self.assertEqual(job.connection_id, self.connection.id)
        self.assertGreaterEqual(job.records_processed, 1)
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNone(job.error_message)

    def test_run_sync_uses_selected_streams_without_discovery(self):
        self.connection.selected_streams = ["test_users"]
        self.session.commit()

        events = []
        source = MagicMock(spec=["discover", "get_table_schema", "read_records"])
        source.get_table_schema.side_effect = lambda table: events.append(("schema", table)) or [
            {"name": "id", "data_type": "integer", "max_length": None, "nullable": False},
        ]
        source.read_records.side_effect = lambda *args, **kwargs: events.append(("read", args[0])) or [{"id": 1}]
        destination = MagicMock(spec=["ensure_table_matches_schema", "write_records"])
        destination.ensure_table_matches_schema.side_effect = lambda table, schema: events.append(("ensure", table))

        with patch("app.services.sync_service.get_source_connector") as mock_source_connector, patch("app.services.sync_service.get_destination_connector") as mock_destination_connector:
            mock_source_connector.return_value.return_value = source
            mock_destination_connector.return_value.return_value = destination

            job = self.service.run_sync(self.connection.id)

        self.assertEqual(job.status, "success")
        source.discover.assert_not_called()
        self.assertEqual(events, [("schema", "test_users"), ("ensure", "test_users"), ("read", "test_users")])
        destination.ensure_table_matches_schema.assert_called_once()
        source.read_records.assert_called_once_with("test_users", cursor_field=None, cursor_value=None)
        destination.write_records.assert_called_once_with("test_users", [{"id": 1}])

    def test_list_jobs_returns_connection_history(self):
        earlier = SyncJob(
            connection_id=self.connection.id,
            status="success",
            started_at=datetime.utcnow().isoformat(),
            finished_at=datetime.utcnow().isoformat(),
            records_processed=7,
        )
        self.session.add(earlier)
        self.session.commit()

        jobs = self.service.list_jobs(self.connection.id)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].connection_id, self.connection.id)

    def test_list_schemas_returns_source_or_destination_tables(self):
        source_connector = MagicMock()
        source_connector.discover.return_value = ["customers", "orders"]

        destination_connector = MagicMock()
        destination_connector.discover.return_value = ["analytics_customers", "analytics_orders"]

        with patch("app.services.sync_service.get_source_connector") as mock_source_connector, patch("app.services.sync_service.get_destination_connector") as mock_destination_connector:
            mock_source_connector.return_value.return_value = source_connector
            mock_destination_connector.return_value.return_value = destination_connector

            source_tables = self.service.list_schemas(self.connection.id, "source")
            destination_tables = self.service.list_schemas(self.connection.id, "destination")

        self.assertEqual(source_tables, ["customers", "orders"])
        self.assertEqual(destination_tables, ["analytics_customers", "analytics_orders"])

    def test_preview_table_raises_http_400_for_missing_table(self):
        destination_connector = MagicMock()
        destination_connector.read_records.side_effect = Exception('relation "reception.reception" does not exist')

        with patch("app.services.sync_service.get_destination_connector") as mock_destination_connector:
            mock_destination_connector.return_value.return_value = destination_connector

            with self.assertRaises(Exception) as ctx:
                self.service.preview_table(self.connection.id, "reception", source_or_destination="destination", limit=50)

        self.assertIn("Unable to preview table 'reception'", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
