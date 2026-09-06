from datetime import datetime

from fastapi import HTTPException

from app.connectors.registry import get_destination_connector, get_source_connector
from app.core.encryption import decrypt_config
from app.models import SyncJob, SyncState

# Maximum number of characters to keep in job.logs; older content will be truncated
MAX_LOG_CHARS = 200_000


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

    def run_sync(self, connection_id: int, job_id: int | None = None, refresh: bool = False) -> SyncJob:
        connection = self._get_connection_or_404(connection_id)

        source_def = self.definition_service.get_source(connection.source_id)
        dest_def = self.definition_service.get_destination(connection.destination_id)

        # If a job id was provided (created by the API), attach to it; otherwise create a new job.
        if job_id is not None:
            job = self.db.query(SyncJob).filter(SyncJob.id == job_id).first()
            if not job:
                # fallback to creating a job if not found
                job = SyncJob(
                    connection_id=connection.id,
                    status="running",
                    started_at=datetime.utcnow().isoformat(),
                    records_processed=0,
                )
            else:
                job.status = "running"
                job.started_at = datetime.utcnow().isoformat()
                job.records_processed = 0
        else:
            job = SyncJob(
                connection_id=connection.id,
                status="running",
                started_at=datetime.utcnow().isoformat(),
                records_processed=0,
            )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        def _append_job_log(message: str):
            ts = datetime.utcnow().isoformat()
            existing = job.logs or ""
            new = existing + f"[{ts}] {message}\n"
            # Truncate if logs grow too large, keep the most recent portion
            if len(new) > MAX_LOG_CHARS:
                new = new[-MAX_LOG_CHARS:]
            job.logs = new
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

        _append_job_log("Job started")

        try:
            source_config = decrypt_config(connection.source_connection_json)
            dest_config = decrypt_config(connection.destination_connection_json)

            SourceCls = get_source_connector(source_def.connector_type)
            DestCls = get_destination_connector(dest_def.connector_type)

            source = SourceCls(source_config)
            destination = DestCls(dest_config)

            # Respect user-selected streams if provided on the connection; otherwise discover all
            if getattr(connection, "selected_streams", None):
                configured_streams = connection.selected_streams
                _append_job_log(f"Using user-selected streams: {configured_streams}")
            else:
                configured_streams = source.discover()
                _append_job_log(f"Discovered streams: {configured_streams}")

            total_records = 0

            for stream_entry in configured_streams:
                # support either simple table name strings or dicts with extra config
                if isinstance(stream_entry, dict):
                    table_name = stream_entry.get("name") or stream_entry.get("table")
                    cursor_field = stream_entry.get("cursor_field")
                else:
                    table_name = stream_entry
                    cursor_field = None

                _append_job_log(f"Syncing stream: {table_name} (cursor_field={cursor_field})")

                get_table_schema = getattr(source, "get_table_schema", None)
                ensure_table_matches_schema = getattr(destination, "ensure_table_matches_schema", None)
                if callable(get_table_schema) and callable(ensure_table_matches_schema):
                    source_schema = get_table_schema(table_name)
                    ensure_table_matches_schema(table_name, source_schema)
                    _append_job_log(f"Prepared destination table: {table_name}")

                if refresh:
                    truncate_table = getattr(destination, "truncate_table", None)
                    if not callable(truncate_table):
                        raise ValueError("The destination connector does not support full refreshes")
                    truncate_table(table_name)
                    _append_job_log(f"Refreshed destination table: {table_name}")

                # Load last sync state for this connection+table
                state = (
                    self.db.query(SyncState)
                    .filter(SyncState.connection_id == connection.id, SyncState.table_name == table_name)
                    .first()
                )
                if not state:
                    state = SyncState(connection_id=connection.id, table_name=table_name, cursor_field=cursor_field, cursor_value=None)
                    self.db.add(state)
                    self.db.commit()
                    self.db.refresh(state)

                if refresh:
                    state.cursor_value = None
                    state.cursor_field = cursor_field
                    self.db.add(state)
                    self.db.commit()
                    self.db.refresh(state)

                cursor_value = state.cursor_value if state.cursor_value else None

                # Pass cursor info to source.read_records for incremental reads
                records = list(source.read_records(table_name, cursor_field=cursor_field, cursor_value=cursor_value))
                _append_job_log(f"Read {len(records)} records from source for {table_name}")

                if records:
                    destination.write_records(table_name, records)
                    _append_job_log(f"Wrote {len(records)} records to destination for {table_name}")
                    total_records += len(records)

                    # Update sync state cursor_value if we have a cursor_field
                    if cursor_field and records:
                        last_val = records[-1].get(cursor_field)
                        if last_val is not None:
                            state.cursor_field = cursor_field
                            state.cursor_value = str(last_val)
                            self.db.add(state)
                            self.db.commit()
                            self.db.refresh(state)
                            _append_job_log(f"Updated sync state for {table_name}: cursor_value={state.cursor_value}")

            _append_job_log(f"Sync finished, total records processed: {total_records}")

            job.status = "success"
            job.records_processed = total_records
            job.finished_at = datetime.utcnow().isoformat()
            job.error_message = None

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.utcnow().isoformat()
            _append_job_log(f"Sync failed: {exc}")

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def create_retry_job(self, connection_id: int, failed_job_id: int) -> SyncJob:
        connection = self._get_connection_or_404(connection_id)
        failed_job = (
            self.db.query(SyncJob)
            .filter(SyncJob.id == failed_job_id, SyncJob.connection_id == connection.id)
            .first()
        )
        if not failed_job:
            raise HTTPException(status_code=404, detail="Sync job not found")
        if failed_job.status != "failed":
            raise HTTPException(status_code=400, detail="Only failed sync jobs can be retried")

        retry_job = SyncJob(
            connection_id=connection.id,
            status="queued",
            started_at=None,
            records_processed=0,
            logs=f"Retrying failed job {failed_job.id}\n",
        )
        self.db.add(retry_job)
        self.db.commit()
        self.db.refresh(retry_job)
        return retry_job

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
