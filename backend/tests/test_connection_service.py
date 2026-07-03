import os
import sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base_class import Base
from app.exceptions import BusinessRuleError, ConnectionNotFoundError
from app.models import Connection, DestinationDefinition, Project, SourceDefinition
from app.repositories.connection_repository import ConnectionRepository
from app.schemas.connection import ConnectionCreate, ConnectionUpdate
from app.services.connection_service import ConnectionService


class ConnectionServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.session = self.Session()
        self.repository = ConnectionRepository(self.session)
        self.service = ConnectionService(self.repository)

        self.source = SourceDefinition(name="Stripe")
        self.destination = DestinationDefinition(name="Postgres")
        self.project = Project(name="Demo Project")
        self.session.add_all([self.source, self.destination, self.project])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_create_connection_requires_valid_references(self):
        dto = ConnectionCreate(
            source_id=999,
            destination_id=self.destination.id,
            project_id=self.project.id,
        )

        with self.assertRaises(BusinessRuleError):
            self.service.create(dto)

    def test_get_missing_connection_raises_not_found(self):
        with self.assertRaises(ConnectionNotFoundError):
            self.service.get(999)

    def test_create_connection_persists_valid_data(self):
        dto = ConnectionCreate(
            source_id=self.source.id,
            destination_id=self.destination.id,
            project_id=self.project.id,
            schedule="0 * * * *",
        )

        connection = self.service.create(dto)

        self.assertEqual(connection.source_id, self.source.id)
        self.assertEqual(connection.destination_id, self.destination.id)
        self.assertEqual(connection.project_id, self.project.id)
        self.assertEqual(connection.schedule, "0 * * * *")


if __name__ == "__main__":
    unittest.main()
