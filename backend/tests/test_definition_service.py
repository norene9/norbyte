import os
import sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base_class import Base
from app.exceptions import DestinationDefinitionNotFoundError, SourceDefinitionNotFoundError
from app.repositories.definition_repository import DefinitionRepository
from app.routers.definitions import parse_config_json
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

    def test_parse_config_json_handles_empty_and_valid_payloads(self):
        self.assertIsNone(parse_config_json(""))
        self.assertIsNone(parse_config_json("   "))
        self.assertEqual(parse_config_json('{"api_key": "secret"}'), {"api_key": "secret"})

    def test_source_definition_crud_flow(self):
        created = self.service.create_source(SourceDefinitionCreate(name="Stripe", config_json={"api_key": "secret"}, connector_type="stripe"))
        self.assertEqual(created.name, "Stripe")
        self.assertEqual(created.config_json, {"api_key": "secret"})

        fetched = self.service.get_source(created.id)
        self.assertEqual(fetched.id, created.id)

        updated = self.service.update_source(created.id, SourceDefinitionUpdate(name="Stripe Updated", config_json={"api_key": "new-secret"}, connector_type="stripe"))
        self.assertEqual(updated.name, "Stripe Updated")
        self.assertEqual(updated.config_json, {"api_key": "new-secret"})

        self.service.delete_source(created.id)
        with self.assertRaises(SourceDefinitionNotFoundError):
            self.service.get_source(created.id)

    def test_definition_response_allows_null_connector_type(self):
        source = self.service.create_source(SourceDefinitionCreate(name="Null Connector", connector_type=None))
        destination = self.service.create_destination(DestinationDefinitionCreate(name="Null Destination", connector_type=None))

        self.assertIsNone(source.connector_type)
        self.assertIsNone(destination.connector_type)
        self.assertIsNone(self.service.list_sources()[0].connector_type)
        self.assertIsNone(self.service.list_destinations()[0].connector_type)

    def test_destination_definition_crud_flow(self):
        created = self.service.create_destination(DestinationDefinitionCreate(name="Postgres", config_json={"host": "db.local"}, connector_type="postgres"))
        self.assertEqual(created.name, "Postgres")
        self.assertEqual(created.config_json, {"host": "db.local"})

        fetched = self.service.get_destination(created.id)
        self.assertEqual(fetched.id, created.id)

        updated = self.service.update_destination(created.id, DestinationDefinitionUpdate(name="Snowflake", config_json={"host": "snowflake.local"}, connector_type="postgres"))
        self.assertEqual(updated.name, "Snowflake")
        self.assertEqual(updated.config_json, {"host": "snowflake.local"})

        self.service.delete_destination(created.id)
        with self.assertRaises(DestinationDefinitionNotFoundError):
            self.service.get_destination(created.id)


if __name__ == "__main__":
    unittest.main()
