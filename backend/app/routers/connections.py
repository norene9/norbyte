from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories import ConnectionRepository
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionUpdate
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["connections"])


def get_connection_service(db: Session = Depends(get_db)) -> ConnectionService:
    return ConnectionService(ConnectionRepository(db))


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
