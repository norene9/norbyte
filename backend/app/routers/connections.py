import asyncio
import json
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
import time
from sqlalchemy.orm import Session

from app.dependencies import get_connection_service, get_sync_service
from app.db.session import get_db
from app.models import SyncJob
from app.repositories import DefinitionRepository
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionUpdate, ConnectionWithSyncJobResponse
from app.schemas.sync_job import SyncJobResponse
from app.services.connection_service import ConnectionService
from app.services.sync_service import SyncService
from app.db.session import SessionLocal

router = APIRouter(prefix="/connections", tags=["connections"])


def _parse_json_object(raw_value: str, field_name: str) -> dict:
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail=f"{field_name} must be a JSON object.")
    return parsed


def _parse_json_list(raw_value: str | None, field_name: str) -> list | None:
    if raw_value is None or raw_value.strip() == "":
        return None
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} must be valid JSON.") from exc
    if not isinstance(parsed, list):
        raise HTTPException(status_code=422, detail=f"{field_name} must be a JSON array.")
    return parsed


@router.post("/", response_model=ConnectionResponse)
def create_connection(
    connection: ConnectionCreate,
    service: ConnectionService = Depends(get_connection_service),
):
    return service.create(connection)


@router.post("/upload-data-file", response_model=ConnectionWithSyncJobResponse)
def create_connection_from_data_file(
    files: Annotated[List[UploadFile], File(...)],
    source_id: int = Form(...),
    destination_id: int = Form(...),
    destination_connection_json: str = Form(...),
    project_id: int | None = Form(None),
    schedule: str | None = Form(None),
    destination_table_prefix: str | None = Form(None),
    selected_streams: str | None = Form(None),
    db: Session = Depends(get_db),
    connection_service: ConnectionService = Depends(get_connection_service),
    sync_service: SyncService = Depends(get_sync_service),
):
    """Upload one or more CSV/Excel files (each becomes its own stream), create a
    connection for it the same way as other source types (linked to a project
    and destination), and immediately load the data into the destination."""
    try:
        source_config = DefinitionRepository(db).save_data_files(files)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    dto = ConnectionCreate(
        source_id=source_id,
        destination_id=destination_id,
        project_id=project_id,
        schedule=schedule,
        source_connection_json=source_config,
        destination_connection_json=_parse_json_object(destination_connection_json, "destination_connection_json"),
        destination_table_prefix=destination_table_prefix,
        selected_streams=_parse_json_list(selected_streams, "selected_streams"),
    )
    connection = connection_service.create(dto)

    job = SyncJob(connection_id=connection.id, status="queued", started_at=None, records_processed=0, logs="")
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        from app.tasks.celery_worker import run_sync_task

        run_sync_task.delay(connection.id, job.id, False)
    except Exception:
        job = sync_service.run_sync(connection.id, job_id=job.id, refresh=False)

    return {"connection": connection, "sync_job": job}


@router.get("/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: int,
    service: ConnectionService = Depends(get_connection_service),
):
    return service.get(connection_id)


@router.get("/", response_model=list[ConnectionResponse])
def list_connections(
    service: ConnectionService = Depends(get_connection_service),
):
    return service.list()


@router.put("/{connection_id}", response_model=ConnectionResponse)
def update_connection(
    connection_id: int,
    connection: ConnectionUpdate,
    service: ConnectionService = Depends(get_connection_service),
):
    return service.update(connection_id, connection)


@router.delete("/{connection_id}")
def delete_connection(
    connection_id: int,
    service: ConnectionService = Depends(get_connection_service),
):
    service.delete(connection_id)
    return {"message": "Connection deleted successfully"}


@router.post("/{connection_id}/sync", response_model=SyncJobResponse)
def trigger_sync(
    connection_id: int,
    refresh: bool = Query(False),
    selected_streams: list[dict | str] | None = Body(None, embed=True),
    service: SyncService = Depends(get_sync_service),
):
    # Let callers pick which streams to sync at trigger time instead of only at connection creation
    if selected_streams is not None:
        connection = service._get_connection_or_404(connection_id)
        connection.selected_streams = selected_streams
        service.db.add(connection)
        service.db.commit()

    # Create a queued job record so callers get an immediate job id/status
    job = SyncJob(connection_id=connection_id, status="queued", started_at=None, records_processed=0, logs="")
    service.db.add(job)
    service.db.commit()
    service.db.refresh(job)

    # Enqueue the Celery worker to perform the sync and update the job
    try:
        from app.tasks.celery_worker import run_sync_task

        run_sync_task.delay(connection_id, job.id, refresh)
    except Exception:
        # If Celery isn't available, fall back to running synchronously
        service.run_sync(connection_id, job_id=job.id, refresh=refresh)

    return job


@router.post("/{connection_id}/jobs/{job_id}/retry", response_model=SyncJobResponse)
def retry_sync(
    connection_id: int,
    job_id: int,
    service: SyncService = Depends(get_sync_service),
):
    job = service.create_retry_job(connection_id, job_id)
    try:
        from app.tasks.celery_worker import run_sync_task

        run_sync_task.delay(connection_id, job.id)
    except Exception:
        service.run_sync(connection_id, job_id=job.id)
    return job


@router.get("/{connection_id}/jobs", response_model=list[SyncJobResponse])
def list_sync_jobs(
    connection_id: int,
    service: SyncService = Depends(get_sync_service),
):
    return service.list_jobs(connection_id)


@router.get("/{connection_id}/jobs/{job_id}/logs/stream")
async def stream_job_logs(
    connection_id: int,
    job_id: int,
    service: SyncService = Depends(get_sync_service),
):
    """Server-Sent Events endpoint to stream incremental logs for a job. Polls the DB every second."""

    async def event_stream():
        last_len = 0
        max_iterations = 300 
        for _ in range(max_iterations):
            db = SessionLocal() #fresh session for each iteration
            try:
                job = (
                    db.query(SyncJob).filter(SyncJob.id == job_id, SyncJob.connection_id == connection_id).first()
                )
                if not job:
                    yield "event: error\n"
                    yield "data: Job not found\n\n"
                    return
                if job.status in ("success", "failed"):
                    logs = job.logs or ""
                    if len(logs) > last_len:
                        new = logs[last_len:]
                        last_len = len(logs)
                        for line in new.splitlines(True):
                            yield f"data: {line}\n\n"
                    return
            finally:
                db.close()
            await asyncio.sleep(1)  # Use asyncio.sleep for async context
        yield "event: timeout\ndata: Streaming timeout after 5 minutes\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{connection_id}/schemas")
def list_connection_schemas(
    connection_id: int,
    source_or_destination: str = Query("source", pattern="^(source|destination)$"),
    limit: int | None = Query(None, ge=1),
    offset: int = Query(0, ge=0),
    service: SyncService = Depends(get_sync_service),
):
    return service.list_schemas(connection_id, source_or_destination, limit=limit, offset=offset)


@router.get("/{connection_id}/preview/{table}")
def preview_destination_data(
    connection_id: int,
    table: str,
    source_or_destination: str = Query("destination", pattern="^(source|destination)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: SyncService = Depends(get_sync_service),
):
    return service.preview_table(
        connection_id,
        table,
        source_or_destination=source_or_destination,
        limit=limit,
        offset=offset,
    )

