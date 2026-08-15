from fastapi import APIRouter, Depends, Query

from app.dependencies import get_connection_service, get_sync_service
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionUpdate
from app.schemas.sync_job import SyncJobResponse
from app.services.connection_service import ConnectionService
from app.services.sync_service import SyncService

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
    service: SyncService = Depends(get_sync_service),
):
    return service.run_sync(connection_id)


@router.get("/{connection_id}/jobs", response_model=list[SyncJobResponse])
def list_sync_jobs(
    connection_id: int,
    service: SyncService = Depends(get_sync_service),
):
    return service.list_jobs(connection_id)


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

