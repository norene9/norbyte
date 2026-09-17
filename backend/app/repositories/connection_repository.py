from sqlalchemy.orm import Session
from app.core.encryption import decrypt_config
from app.models import Connection, Schema, SyncJob, SyncState
from app.repositories.definition_repository import DefinitionRepository
from app.schemas.connection import ConnectionCreate, ConnectionUpdate

FILE_SOURCE_CONNECTOR_TYPE = "file_upload"


class ConnectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, dto: ConnectionCreate | dict) -> Connection:
        data = dto.model_dump() if hasattr(dto, "model_dump") else dto
        connection = Connection(**data)
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def get_by_id(self, connection_id: int):
        return self.db.query(Connection).filter(Connection.id == connection_id).first()

    def list(self) -> list[Connection]:
        return self.db.query(Connection).all()

    def update(self, connection: Connection, dto: ConnectionUpdate) -> Connection:
        update_data = dto.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(connection, key, value)

        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def delete(self, connection: Connection) -> None:
        self._delete_source_data_file_if_any(connection)
        # Manually remove dependents first since the FKs have no ON DELETE CASCADE
        self.db.query(SyncState).filter(SyncState.connection_id == connection.id).delete()
        self.db.query(SyncJob).filter(SyncJob.connection_id == connection.id).delete()
        self.db.query(Schema).filter(Schema.connection_id == connection.id).delete()
        self.db.delete(connection)
        self.db.commit()

    def _delete_source_data_file_if_any(self, connection: Connection) -> None:
        source_definition = connection.source_definition
        if not source_definition or source_definition.connector_type != FILE_SOURCE_CONNECTOR_TYPE:
            return

        config = decrypt_config(connection.source_connection_json)
        repo = DefinitionRepository(self.db)

        if "files" in config:
            for entry in config["files"]:
                if entry.get("file_path"):
                    repo.delete_data_file(entry["file_path"])
        elif config.get("file_path"):
            repo.delete_data_file(config["file_path"])
