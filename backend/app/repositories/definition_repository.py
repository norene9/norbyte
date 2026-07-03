from sqlalchemy.orm import Session
from app.models import DestinationDefinition, SourceDefinition
from app.schemas.destination_definition import DestinationDefinitionCreate, DestinationDefinitionUpdate
from app.schemas.source_definition import SourceDefinitionCreate, SourceDefinitionUpdate


class DefinitionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_source(self, dto: SourceDefinitionCreate) -> SourceDefinition:
        source = SourceDefinition(**dto.model_dump())
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_source_by_id(self, source_id: int):
        return self.db.query(SourceDefinition).filter(SourceDefinition.id == source_id).first()

    def list_sources(self) -> list[SourceDefinition]:
        return self.db.query(SourceDefinition).all()

    def update_source(self, source: SourceDefinition, dto: SourceDefinitionUpdate) -> SourceDefinition:
        update_data = dto.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(source, key, value)

        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete_source(self, source: SourceDefinition) -> None:
        self.db.delete(source)
        self.db.commit()

    def create_destination(self, dto: DestinationDefinitionCreate) -> DestinationDefinition:
        destination = DestinationDefinition(**dto.model_dump())
        self.db.add(destination)
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def get_destination_by_id(self, destination_id: int):
        return self.db.query(DestinationDefinition).filter(DestinationDefinition.id == destination_id).first()

    def list_destinations(self) -> list[DestinationDefinition]:
        return self.db.query(DestinationDefinition).all()

    def update_destination(self, destination: DestinationDefinition, dto: DestinationDefinitionUpdate) -> DestinationDefinition:
        update_data = dto.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(destination, key, value)

        self.db.add(destination)
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def delete_destination(self, destination: DestinationDefinition) -> None:
        self.db.delete(destination)
        self.db.commit()
