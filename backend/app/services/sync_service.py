from datetime import datetime

from fastapi import HTTPException

from app.connectors.registry import get_destination_connector, get_source_connector
from app.core.encryption import decrypt_config
from app.models import SyncJob


class SyncService:
    def __init__(self, db, connection_repo, definition_service):
        self.db = db
        self.connection_repo = connection_repo
        self.definition_service = definition_service

    def _get_connection_or_404(self, connection_id: int):
        connection = self.connection_repo.get_by_id(connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        return connection

    def list_schemas(self, connection_id: int, source_or_destination: str = "source") -> list[str]:
        connection = self._get_connection_or_404(connection_id)
        normalized = (source_or_destination or "source").lower()

        if normalized == "source":
            definition = self.definition_service.get_source(connection.source_id)
            config = decrypt_config(connection.source_connection_json)
            connector_cls = get_source_connector(definition.connector_type)
            connector = connector_cls(config)
        elif normalized == "destination":
            definition = self.definition_service.get_destination(connection.destination_id)
            config = decrypt_config(connection.destination_connection_json)
            connector_cls = get_destination_connector(definition.connector_type)
            connector = connector_cls(config)
        else:
            raise HTTPException(status_code=400, detail="source_or_destination must be 'source' or 'destination'")

        if not hasattr(connector, "discover"):
            raise HTTPException(status_code=400, detail=f"{normalized.title()} connector does not support schema discovery")

        return connector.discover()

    def run_sync(self, connection_id: int) -> SyncJob:
        connection = self._get_connection_or_404(connection_id)

        source_def = self.definition_service.get_source(connection.source_id)
        dest_def = self.definition_service.get_destination(connection.destination_id)

        job = SyncJob(
            connection_id=connection.id,
            status="running",
            started_at=datetime.utcnow().isoformat(),
            records_processed=0,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        try:
            source_config = decrypt_config(connection.source_connection_json)
            dest_config = decrypt_config(connection.destination_connection_json)

            SourceCls = get_source_connector(source_def.connector_type)
            DestCls = get_destination_connector(dest_def.connector_type)

            source = SourceCls(source_config)
            destination = DestCls(dest_config)

            tables = source.discover()
            total_records = 0

            for table in tables:
                records = list(source.read_records(table))
                if records:
                    destination.write_records(table, records)
                    total_records += len(records)

            job.status = "success"
            job.records_processed = total_records
            job.finished_at = datetime.utcnow().isoformat()
            job.error_message = None

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.utcnow().isoformat()

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs(self, connection_id: int) -> list[SyncJob]:
        return (
            self.db.query(SyncJob)
            .filter(SyncJob.connection_id == connection_id)
            .order_by(SyncJob.id.desc())
            .all()
        )

    def preview_table(self, connection_id: int, table: str, source_or_destination: str = "destination", limit: int = 50):
        connection = self._get_connection_or_404(connection_id)
        normalized = (source_or_destination or "destination").lower()

        try:
            if normalized == "source":
                definition = self.definition_service.get_source(connection.source_id)
                config = decrypt_config(connection.source_connection_json)
                connector_cls = get_source_connector(definition.connector_type)
                connector = connector_cls(config)
                if not hasattr(connector, "read_records"):
                    raise HTTPException(status_code=400, detail="Source connector does not support previews")
                rows = list(connector.read_records(table))
                return rows[:limit]

            definition = self.definition_service.get_destination(connection.destination_id)
            config = decrypt_config(connection.destination_connection_json)
            connector_cls = get_destination_connector(definition.connector_type)
            connector = connector_cls(config)

            if not hasattr(connector, "read_records"):
                raise HTTPException(status_code=400, detail="Destination connector does not support previews")

            return connector.read_records(table, limit=limit)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to preview table '{table}' from the {normalized} connection: {exc}",
            ) from exc
