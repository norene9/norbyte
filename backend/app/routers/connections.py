import asyncio

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import time

from app.dependencies import get_connection_service, get_sync_service
from app.models import SyncJob
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionUpdate
from app.schemas.sync_job import SyncJobResponse
from app.services.connection_service import ConnectionService
from app.services.sync_service import SyncService
from app.db.session import SessionLocal

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post("/", response_model=ConnectionResponse)
def create_connection(
    connection: ConnectionCreate,
    service: ConnectionService = Depends(get_connection_service),
):
    return service.create(connection)


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
    service: SyncService = Depends(get_sync_service),
):
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


@router.get("/{connection_id}/schemas", response_model=list[str])
def list_connection_schemas(
    connection_id: int,
    source_or_destination: str = Query("source", pattern="^(source|destination)$"),
    service: SyncService = Depends(get_sync_service),
):
    return service.list_schemas(connection_id, source_or_destination)


@router.get("/{connection_id}/preview/{table}")
def preview_destination_data(
    connection_id: int,
    table: str,
    source_or_destination: str = Query("destination", pattern="^(source|destination)$"),
    limit: int = Query(50, ge=1, le=200),
    service: SyncService = Depends(get_sync_service),
):
    return service.preview_table(connection_id, table, source_or_destination=source_or_destination, limit=limit)

