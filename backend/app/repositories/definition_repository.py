from sqlalchemy.orm import Session
from app.models import DestinationDefinition, SourceDefinition
from app.schemas.destination_definition import DestinationDefinitionCreate, DestinationDefinitionUpdate
from app.schemas.source_definition import SourceDefinitionCreate, SourceDefinitionUpdate
from fastapi import UploadFile
import os
import uuid
SOURCES_DIR = "/data/uploads/sources"
DESTINATIONS_DIR = "/data/uploads/destinations"

os.makedirs(SOURCES_DIR, exist_ok=True)
os.makedirs(DESTINATIONS_DIR, exist_ok=True)

class DefinitionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_source(self, dto: SourceDefinitionCreate,logo_file: UploadFile | None = None) -> SourceDefinition:
        data = dto.model_dump()
        if logo_file:
            ext = logo_file.filename.split(".")[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(SOURCES_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(logo_file.file.read())

            data["logo"] = filepath
        source = SourceDefinition(**data)
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_source_by_id(self, source_id: int):
        return self.db.query(SourceDefinition).filter(SourceDefinition.id == source_id).first()

    def list_sources(self) -> list[SourceDefinition]:
        return self.db.query(SourceDefinition).all()

    def update_source(self, source: SourceDefinition, dto: SourceDefinitionUpdate,logo_file: UploadFile | None = None) -> SourceDefinition:
        update_data = dto.model_dump(exclude_unset=True)
        if logo_file:
            # delete the old logo file, if there is one
            if source.logo:
                old_path = source.logo.lstrip("/")  # strip leading slash if you store "/sources/xxx.png"
                if os.path.exists(old_path):
                    os.remove(old_path)

            ext = logo_file.filename.split(".")[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(SOURCES_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(logo_file.file.read())

            update_data["logo"] = f"/{filepath}"

        for key, value in update_data.items():
            setattr(source, key, value)

        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete_source(self, source: SourceDefinition) -> None:
        if source.logo:
                old_path = source.logo.lstrip("/")  # strip leading slash if you store "/sources/xxx.png"
                if os.path.exists(old_path):
                    os.remove(old_path)
        self.db.delete(source)
        self.db.commit()

    def create_destination(self, dto: DestinationDefinitionCreate,logo_file : UploadFile |None = None) -> DestinationDefinition:
        data = dto.model_dump()
        if logo_file:
            ext = logo_file.filename.split(".")[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(DESTINATIONS_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(logo_file.file.read())

            data["logo"] = filepath
        destination = DestinationDefinition(**data)
        self.db.add(destination)
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def get_destination_by_id(self, destination_id: int):
        return self.db.query(DestinationDefinition).filter(DestinationDefinition.id == destination_id).first()

    def list_destinations(self) -> list[DestinationDefinition]:
        return self.db.query(DestinationDefinition).all()

    def update_destination(self, destination: DestinationDefinition, dto: DestinationDefinitionUpdate,
                           logo_file: UploadFile | None = None) -> DestinationDefinition:
        update_data = dto.model_dump(exclude_unset=True)
        if logo_file:
            # delete the old logo file, if there is one
            if destination.logo:
                old_path = destination.logo.lstrip("/")  # strip leading slash if you store "/destinations/xxx.png"
                if os.path.exists(old_path):
                    os.remove(old_path)

            ext = logo_file.filename.split(".")[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(DESTINATIONS_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(logo_file.file.read())

            update_data["logo"] = f"/{filepath}"

        for key, value in update_data.items():
            setattr(destination, key, value)

        self.db.add(destination)
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def delete_destination(self, destination: DestinationDefinition) -> None:
        if destination.logo:
            old_path = destination.logo.lstrip("/")  # strip leading slash if you store "/destinations/xxx.png"
            if os.path.exists(old_path):
                os.remove(old_path)
        self.db.delete(destination)
        self.db.commit()
