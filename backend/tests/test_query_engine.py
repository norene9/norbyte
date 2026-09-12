import os
import sys
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base_class import Base
from app.models import SemanticField, SemanticRelationship, SemanticTable
from app.repositories.semantic_repository import SemanticRepository
from app.schemas.query import FilterRequest, MeasureRequest, QueryRequest
from app.services.query_engine import QueryEngine


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.session = self.Session()
        self.repo = SemanticRepository(self.session)
        self.query_engine = QueryEngine(self.repo)

        self.races = SemanticTable(
            id=1,
            project_id=1,
            connection_id=1,
            physical_table="races",
            display_name="races",
        )
        self.session.add(self.races)
        self.session.flush()

        self.races_field = SemanticField(
            semantic_table_id=self.races.id,
            column_name="amount",
            display_name="amount",
            field_type="measure",
            data_type="number",
            default_aggregation="sum",
        )
        self.session.add(self.races_field)

        self.circuits = SemanticTable(
            id=2,
            project_id=1,
            connection_id=1,
            physical_table="circuits",
            display_name="circuits",
        )
        self.session.add(self.circuits)
        self.session.flush()

        self.circuit_field = SemanticField(
            semantic_table_id=self.circuits.id,
            column_name="circuit_id",
            display_name="circuit_id",
            field_type="dimension",
            data_type="string",
        )
        self.session.add(self.circuit_field)

        self.relationship = SemanticRelationship(
            id=1,
            project_id=1,
            name="races_to_circuits",
            from_table_id=self.races.id,
            from_column="circuit_id",
            from_json_path="circuitId",
            to_table_id=self.circuits.id,
            to_column="circuit_id",
            to_json_path=None,
            relationship_type="many_to_one",
        )
        self.session.add(self.relationship)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_build_uses_join_json_path_and_filters(self):
        request = QueryRequest(
            table="races",
            dimensions=["circuit_id"],
            measures=[MeasureRequest(field="amount")],
            filters=[FilterRequest(field="circuit_id", operator="eq", value="A1")],
            joins=["races_to_circuits"],
            limit=100,
        )

        sql, params = self.query_engine.build(1, request)

        self.assertIn('JOIN "circuits" t1', sql)
        self.assertIn("->> 'circuitId'", sql)
        self.assertEqual(params, ["A1"])
        self.assertIn('LIMIT 100', sql)


if __name__ == "__main__":
    unittest.main()
