import os
import sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base_class import Base
from app.exceptions import DestinationDefinitionNotFoundError, SourceDefinitionNotFoundError
from app.repositories.definition_repository import DefinitionRepository
from app.schemas.destination_definition import DestinationDefinitionCreate, DestinationDefinitionUpdate
from app.schemas.source_definition import SourceDefinitionCreate, SourceDefinitionUpdate
from app.services.definition_service import DefinitionService


class DefinitionServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.session = self.Session()
        self.service = DefinitionService(DefinitionRepository(self.session))

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_source_definition_crud_flow(self):
        created = self.service.create_source(SourceDefinitionCreate(name="Stripe"))
        self.assertEqual(created.name, "Stripe")

        fetched = self.service.get_source(created.id)
        self.assertEqual(fetched.id, created.id)

        updated = self.service.update_source(created.id, SourceDefinitionUpdate(name="Stripe Updated"))
        self.assertEqual(updated.name, "Stripe Updated")

        self.service.delete_source(created.id)
        with self.assertRaises(SourceDefinitionNotFoundError):
            self.service.get_source(created.id)

    def test_destination_definition_crud_flow(self):
        created = self.service.create_destination(DestinationDefinitionCreate(name="Postgres"))
        self.assertEqual(created.name, "Postgres")

        fetched = self.service.get_destination(created.id)
        self.assertEqual(fetched.id, created.id)

        updated = self.service.update_destination(created.id, DestinationDefinitionUpdate(name="Snowflake"))
        self.assertEqual(updated.name, "Snowflake")

        self.service.delete_destination(created.id)
        with self.assertRaises(DestinationDefinitionNotFoundError):
            self.service.get_destination(created.id)


if __name__ == "__main__":
    unittest.main()
