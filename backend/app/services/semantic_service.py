from app.connectors.registry import get_destination_connector
from app.core.encryption import decrypt_config
from app.exceptions import NotFoundError
from app.models import SemanticField, SemanticRelationship, SemanticTable
from app.repositories.semantic_repository import SemanticRepository
from app.schemas.semantic import SemanticRelationshipCreate, SemanticTableCreate


NUMERIC_TYPES = {"smallint", "integer", "bigint", "numeric", "real", "double precision", "decimal"}
DATE_TYPES = {"date", "timestamp without time zone", "timestamp with time zone", "time without time zone"}


def suggest_fields_from_table(source_columns: list[dict]) -> list[dict]:
    suggestions = []
    for column in source_columns:
        column_name = column["name"]
        pg_type = column["data_type"]
        is_identifier = column_name == "id" or column_name.endswith("_id")

        if is_identifier:
            field_type, data_type, aggregation = "dimension", "string", None
        elif pg_type in NUMERIC_TYPES:
            field_type, data_type, aggregation = "measure", "number", "sum"
        elif pg_type in DATE_TYPES:
            field_type, data_type, aggregation = "dimension", "date", None
        elif pg_type == "boolean":
            field_type, data_type, aggregation = "dimension", "boolean", None
        else:
            field_type, data_type, aggregation = "dimension", "string", None

        suggestions.append({
            "column_name": column_name,
            "display_name": column_name.replace("_", " ").title(),
            "field_type": field_type,
            "data_type": data_type,
            "default_aggregation": aggregation,
            "is_hidden": is_identifier or column_name in {"created_at", "updated_at"},
        })
    return suggestions


class SemanticService:
    def __init__(self, repository: SemanticRepository, connection_repository, definition_service):
        self.repository = repository
        self.connection_repository = connection_repository
        self.definition_service = definition_service

    def create_table(self, dto: SemanticTableCreate) -> SemanticTable:
        connection = self.connection_repository.get_by_id(dto.connection_id)
        if not connection or connection.project_id != dto.project_id:
            raise NotFoundError("Connection not found in project")

        semantic_table = SemanticTable(
            project_id=dto.project_id,
            connection_id=dto.connection_id,
            physical_table=dto.physical_table,
            display_name=dto.display_name,
            description=dto.description,
            fields=[SemanticField(**field.model_dump()) for field in dto.fields],
        )
        return self.repository.create_table(semantic_table)

    def list_tables(self, project_id: int) -> list[SemanticTable]:
        return self.repository.list_tables_by_project(project_id)

    def create_relationship(self, dto: SemanticRelationshipCreate) -> SemanticRelationship:
        from_table = self.repository.get_table_by_id(dto.from_table_id)
        to_table = self.repository.get_table_by_id(dto.to_table_id)
        if not from_table or not to_table or from_table.project_id != dto.project_id or to_table.project_id != dto.project_id:
            raise NotFoundError("Semantic table not found in project")

        relationship = SemanticRelationship(**dto.model_dump())
        return self.repository.create_relationship(relationship)

    def list_relationships(self, project_id: int) -> list[SemanticRelationship]:
        return self.repository.list_relationships_by_project(project_id)

    def suggest_fields(self, connection_id: int, table: str) -> list[dict]:
        connection = self.connection_repository.get_by_id(connection_id)
        if not connection:
            raise NotFoundError("Connection not found")

        destination_definition = self.definition_service.get_destination(connection.destination_id)
        destination = get_destination_connector(destination_definition.connector_type)(
            decrypt_config(connection.destination_connection_json)
        )
        get_table_schema = getattr(destination, "get_table_schema", None)
        if not callable(get_table_schema):
            raise ValueError("The destination connector does not support schema discovery")

        actual_table = f"{connection.destination_table_prefix or ''}{table}"
        return suggest_fields_from_table(get_table_schema(actual_table))