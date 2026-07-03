from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories import DefinitionRepository
from app.schemas.destination_definition import DestinationDefinitionCreate, DestinationDefinitionResponse, DestinationDefinitionUpdate
from app.schemas.source_definition import SourceDefinitionCreate, SourceDefinitionResponse, SourceDefinitionUpdate
from app.services.definition_service import DefinitionService

router = APIRouter(prefix="/definitions", tags=["definitions"])


def get_definition_service(db: Session = Depends(get_db)) -> DefinitionService:
    return DefinitionService(DefinitionRepository(db))


@router.post("/sources/", response_model=SourceDefinitionResponse)
def create_source_definition(
    source: SourceDefinitionCreate,
    service: DefinitionService = Depends(get_definition_service),
):
    return service.create_source(source)


@router.get("/sources/{source_id}", response_model=SourceDefinitionResponse)
def get_source_definition(
    source_id: int,
    service: DefinitionService = Depends(get_definition_service),
):
    return service.get_source(source_id)


@router.get("/sources/", response_model=list[SourceDefinitionResponse])
def list_source_definitions(
    service: DefinitionService = Depends(get_definition_service),
):
    return service.list_sources()


@router.put("/sources/{source_id}", response_model=SourceDefinitionResponse)
def update_source_definition(
    source_id: int,
    source: SourceDefinitionUpdate,
    service: DefinitionService = Depends(get_definition_service),
):
    return service.update_source(source_id, source)


@router.delete("/sources/{source_id}")
def delete_source_definition(
    source_id: int,
    service: DefinitionService = Depends(get_definition_service),
):
    service.delete_source(source_id)
    return {"message": "Source definition deleted successfully"}


@router.post("/destinations/", response_model=DestinationDefinitionResponse)
def create_destination_definition(
    destination: DestinationDefinitionCreate,
    service: DefinitionService = Depends(get_definition_service),
):
    return service.create_destination(destination)


@router.get("/destinations/{destination_id}", response_model=DestinationDefinitionResponse)
def get_destination_definition(
    destination_id: int,
    service: DefinitionService = Depends(get_definition_service),
):
    return service.get_destination(destination_id)


@router.get("/destinations/", response_model=list[DestinationDefinitionResponse])
def list_destination_definitions(
    service: DefinitionService = Depends(get_definition_service),
):
    return service.list_destinations()


@router.put("/destinations/{destination_id}", response_model=DestinationDefinitionResponse)
def update_destination_definition(
    destination_id: int,
    destination: DestinationDefinitionUpdate,
    service: DefinitionService = Depends(get_definition_service),
):
    return service.update_destination(destination_id, destination)


@router.delete("/destinations/{destination_id}")
def delete_destination_definition(
    destination_id: int,
    service: DefinitionService = Depends(get_definition_service),
):
    service.delete_destination(destination_id)
    return {"message": "Destination definition deleted successfully"}
