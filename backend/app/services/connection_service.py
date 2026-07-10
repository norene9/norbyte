from app.exceptions import BusinessRuleError, ConnectionNotFoundError
from app.models import Connection, DestinationDefinition, Project, SourceDefinition
from app.repositories.connection_repository import ConnectionRepository
from app.schemas.connection import ConnectionCreate, ConnectionUpdate


class ConnectionService:
    def __init__(self, repository: ConnectionRepository):
        self.repository = repository

    def create(self, dto: ConnectionCreate) -> Connection:
        self._validate_source(dto.source_id)
        self._validate_destination(dto.destination_id)
        self._validate_project(dto.project_id)
        return self.repository.create(dto)

    def get(self, connection_id: int) -> Connection:
        connection = self.repository.get_by_id(connection_id)
        if not connection:
            raise ConnectionNotFoundError(connection_id)
        return connection

    def list(self) -> list[Connection]:
        return self.repository.list()

    def update(self, connection_id: int, dto: ConnectionUpdate) -> Connection:
        connection = self.get(connection_id)
        return self.repository.update(connection, dto)

    def delete(self, connection_id: int) -> None:
        connection = self.get(connection_id)
        self.repository.delete(connection)

    def _validate_source(self, source_id: int) -> None:
        if not self._exists(SourceDefinition, source_id):
            raise BusinessRuleError("Source definition not found")

    def _validate_destination(self, destination_id: int) -> None:
        if not self._exists(DestinationDefinition, destination_id):
            raise BusinessRuleError("Destination definition not found")

    def _validate_project(self, project_id: int) -> None:
        if not self._exists(Project, project_id):
            raise BusinessRuleError("Project not found")

    def _exists(self, model, model_id: int) -> bool:
        return self.repository.db.query(model).filter(model.id == model_id).first() is not None
