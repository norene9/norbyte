import os
import sys
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base_class import Base
from app.exceptions import NotFoundError
from app.models import SemanticField, SemanticRelationship, SemanticTable
from app.repositories.semantic_repository import SemanticRepository
from app.services.semantic_service import SemanticService


class SemanticServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.session = sessionmaker(bind=self.engine)()
        Base.metadata.create_all(self.engine)
        self.repository = SemanticRepository(self.session)
        self.service = SemanticService(self.repository, None, None)

        self.races = SemanticTable(
            project_id=1,
            connection_id=1,
            physical_table="races",
            display_name="Races",
            fields=[
                SemanticField(column_name="season", display_name="Season", field_type="dimension", data_type="string"),
                SemanticField(column_name="race_name", display_name="Race Name", field_type="dimension", data_type="string"),
                SemanticField(column_name="internal_id", display_name="Internal ID", field_type="dimension", data_type="string", is_hidden=True),
                SemanticField(column_name="lap_count", display_name="Lap Count", field_type="measure", data_type="number", default_aggregation="sum"),
                SemanticField(column_name="hidden_amount", display_name="Hidden Amount", field_type="measure", data_type="number", is_hidden=True),
            ],
        )
        self.circuits = SemanticTable(
            project_id=1,
            connection_id=1,
            physical_table="circuits",
            display_name="Circuits",
        )
        self.session.add_all([self.races, self.circuits])
        self.session.flush()
        self.session.add(SemanticRelationship(
            project_id=1,
            name="races_to_circuits",
            from_table_id=self.races.id,
            from_column="circuit_id",
            to_table_id=self.circuits.id,
            to_column="circuit_id",
            relationship_type="many_to_one",
        ))
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_get_query_options_returns_visible_fields_and_outbound_joins(self):
        options = self.service.get_query_options(self.races.id)

        self.assertEqual(options["table"], "Races")
        self.assertEqual(options["dimensions"], [
            {"field": "season", "display_name": "Season", "data_type": "string"},
            {"field": "race_name", "display_name": "Race Name", "data_type": "string"},
        ])
        self.assertEqual(options["measures"], [{
            "field": "lap_count",
            "display_name": "Lap Count",
            "default_aggregation": "sum",
            "allowed_aggregations": ["sum", "avg", "count", "min", "max"],
        }])
        self.assertEqual(options["joins"], [{
            "name": "races_to_circuits",
            "to_table": "Circuits",
            "relationship_type": "many_to_one",
        }])
        self.assertTrue(options["supports_count_all"])

    def test_get_project_query_options_returns_each_project_table(self):
        options = self.service.get_project_query_options(1)

        self.assertEqual([table["table"] for table in options], ["Races", "Circuits"])

    def test_get_query_options_rejects_unknown_table(self):
        with self.assertRaises(NotFoundError):
            self.service.get_query_options(999)


if __name__ == "__main__":
    unittest.main()