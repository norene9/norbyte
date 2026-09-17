from app.connectors.registry import get_destination_connector
from app.core.encryption import decrypt_config, encrypt_config
from app.exceptions import BusinessRuleError, ConnectionNotFoundError
from app.models import Connection, DestinationDefinition, Project, SourceDefinition
from app.repositories.connection_repository import ConnectionRepository
from app.schemas.connection import ConnectionCreate, ConnectionUpdate
from app.services.connection_test import test_destination_connection, test_source_connection


class ConnectionService:
    def __init__(self, repository: ConnectionRepository):
        self.repository = repository

    def _decrypt_connection_payloads(self, connection: Connection) -> Connection:
        if not connection:
            return connection

        decrypted = Connection(
            id=connection.id,
            destination_id=connection.destination_id,
            source_id=connection.source_id,
            project_id=connection.project_id,
            schedule=connection.schedule,
            selected_streams=connection.selected_streams,
            destination_table_prefix=connection.destination_table_prefix,
            source_connection_json=decrypt_config(connection.source_connection_json) if connection.source_connection_json else None,
            destination_connection_json=decrypt_config(connection.destination_connection_json) if connection.destination_connection_json else None,
        )
        return decrypted

    def create(self, dto: ConnectionCreate) -> Connection:
        self._validate_source(dto.source_id)
        self._validate_destination(dto.destination_id)
        if dto.project_id is not None:
            self._validate_project(dto.project_id)

        source_definition = self.repository.db.query(SourceDefinition).filter(SourceDefinition.id == dto.source_id).first()
        destination_definition = self.repository.db.query(DestinationDefinition).filter(DestinationDefinition.id == dto.destination_id).first()

        if not source_definition or not source_definition.connector_type:
            raise BusinessRuleError("Source definition connector type is not configured")
        if not destination_definition or not destination_definition.connector_type:
            raise BusinessRuleError("Destination definition connector type is not configured")
        if not dto.source_connection_json:
            raise BusinessRuleError("Source connection config is required")
        if not dto.destination_connection_json:
            raise BusinessRuleError("Destination connection config is required")

        test_source_connection(source_definition.connector_type, dto.source_connection_json)
        test_destination_connection(destination_definition.connector_type, dto.destination_connection_json)

        encrypted = dto.model_dump()
        encrypted["source_connection_json"] = encrypt_config(dto.source_connection_json)
        encrypted["destination_connection_json"] = encrypt_config(dto.destination_connection_json)
        connection = self.repository.create(encrypted)
        
        # Generate default prefix if not provided, using the connection's ID
        if not connection.destination_table_prefix:
            connection.destination_table_prefix = f"conn{connection.id}_"
            self.repository.db.add(connection)
            self.repository.db.commit()
            self.repository.db.refresh(connection)
        
        return self._decrypt_connection_payloads(connection)

    def get(self, connection_id: int) -> Connection:
        connection = self.repository.get_by_id(connection_id)
        if not connection:
            raise ConnectionNotFoundError(connection_id)
        
        # Ensure old connections without a prefix get one assigned
        if not connection.destination_table_prefix:
            connection.destination_table_prefix = f"conn{connection.id}_"
            self.repository.db.add(connection)
            self.repository.db.commit()
            self.repository.db.refresh(connection)
        
        return self._decrypt_connection_payloads(connection)

    def list(self) -> list[Connection]:
        connections = self.repository.list()
        result = []
        for connection in connections:
            # Ensure old connections without a prefix get one assigned
            if not connection.destination_table_prefix:
                connection.destination_table_prefix = f"conn{connection.id}_"
                self.repository.db.add(connection)
                self.repository.db.commit()
                self.repository.db.refresh(connection)
            result.append(self._decrypt_connection_payloads(connection))
        return result

    def update(self, connection_id: int, dto: ConnectionUpdate) -> Connection:
        connection = self.repository.get_by_id(connection_id)
        if not connection:
            raise ConnectionNotFoundError(connection_id)

        if dto.source_connection_json is not None:
            source_definition = self.repository.db.query(SourceDefinition).filter(SourceDefinition.id == connection.source_id).first()
            if not source_definition or not source_definition.connector_type:
                raise BusinessRuleError("Source definition connector type is not configured")
            test_source_connection(source_definition.connector_type, dto.source_connection_json)
            dto.source_connection_json = encrypt_config(dto.source_connection_json)

        if dto.destination_connection_json is not None:
            destination_definition = self.repository.db.query(DestinationDefinition).filter(DestinationDefinition.id == connection.destination_id).first()
            if not destination_definition or not destination_definition.connector_type:
                raise BusinessRuleError("Destination definition connector type is not configured")
            test_destination_connection(destination_definition.connector_type, dto.destination_connection_json)
            dto.destination_connection_json = encrypt_config(dto.destination_connection_json)

        updated = self.repository.update(connection, dto)
        return self._decrypt_connection_payloads(updated)

    def delete(self, connection_id: int) -> None:
        connection = self.repository.get_by_id(connection_id)
        if not connection:
            raise ConnectionNotFoundError(connection_id)
        self._drop_destination_tables(connection)
        self.repository.delete(connection)

    def _drop_destination_tables(self, connection: Connection) -> None:
        """Drop the physical destination tables created for this connection's streams."""
        destination_definition = self.repository.db.query(DestinationDefinition).filter(
            DestinationDefinition.id == connection.destination_id
        ).first()
        if not destination_definition or not destination_definition.connector_type:
            return

        try:
            connector_cls = get_destination_connector(destination_definition.connector_type)
            destination_config = decrypt_config(connection.destination_connection_json)
            destination = connector_cls(destination_config)
        except Exception:
            return

        drop_table = getattr(destination, "drop_table", None)
        if not callable(drop_table):
            return

        prefix = connection.destination_table_prefix or ""
        streams = connection.selected_streams or []
        table_names = [
            (entry.get("name") or entry.get("table")) if isinstance(entry, dict) else entry
            for entry in streams
        ]
        if not table_names and hasattr(destination, "discover"):
            try:
                table_names = [
                    table[len(prefix):] for table in destination.discover() if not prefix or table.startswith(prefix)
                ]
            except Exception:
                table_names = []

        for table_name in table_names:
            if not table_name:
                continue
            try:
                drop_table(table_name, table_prefix=prefix)
            except Exception:
                pass

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
    
