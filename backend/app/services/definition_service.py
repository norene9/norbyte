from app.exceptions import DestinationDefinitionNotFoundError, SourceDefinitionNotFoundError
from app.models import DestinationDefinition, SourceDefinition
from app.repositories.definition_repository import DefinitionRepository
from app.schemas.destination_definition import DestinationDefinitionCreate, DestinationDefinitionUpdate
from app.schemas.source_definition import SourceDefinitionCreate, SourceDefinitionUpdate


class DefinitionService:
    def __init__(self, repository: DefinitionRepository):
        self.repository = repository

    def create_source(self, dto: SourceDefinitionCreate) -> SourceDefinition:
        return self.repository.create_source(dto)

    def get_source(self, source_id: int) -> SourceDefinition:
        source = self.repository.get_source_by_id(source_id)
        if not source:
            raise SourceDefinitionNotFoundError(source_id)
        return source

    def list_sources(self) -> list[SourceDefinition]:
        return self.repository.list_sources()

    def update_source(self, source_id: int, dto: SourceDefinitionUpdate) -> SourceDefinition:
        source = self.get_source(source_id)
        return self.repository.update_source(source, dto)

    def delete_source(self, source_id: int) -> None:
        source = self.get_source(source_id)
        self.repository.delete_source(source)

    def create_destination(self, dto: DestinationDefinitionCreate) -> DestinationDefinition:
        return self.repository.create_destination(dto)

    def get_destination(self, destination_id: int) -> DestinationDefinition:
        destination = self.repository.get_destination_by_id(destination_id)
        if not destination:
            raise DestinationDefinitionNotFoundError(destination_id)
        return destination

    def list_destinations(self) -> list[DestinationDefinition]:
        return self.repository.list_destinations()

    def update_destination(self, destination_id: int, dto: DestinationDefinitionUpdate) -> DestinationDefinition:
        destination = self.get_destination(destination_id)
        return self.repository.update_destination(destination, dto)

    def delete_destination(self, destination_id: int) -> None:
        destination = self.get_destination(destination_id)
        self.repository.delete_destination(destination)
