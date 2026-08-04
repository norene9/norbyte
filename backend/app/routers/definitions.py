import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.repositories import DefinitionRepository
from app.schemas.destination_definition import DestinationDefinitionCreate, DestinationDefinitionResponse, DestinationDefinitionUpdate
from app.schemas.source_definition import SourceDefinitionCreate, SourceDefinitionResponse, SourceDefinitionUpdate
from app.services.definition_service import DefinitionService

router = APIRouter(prefix="/definitions", tags=["definitions"])


def parse_config_json(raw_value: str | None) -> dict | None:
    if raw_value is None or raw_value.strip() == "":
        return None

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail="config_json must be valid JSON.",
        ) from exc

    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=422,
            detail="config_json must be a JSON object.",
        )

    return parsed


def get_definition_service(db: Session = Depends(get_db)) -> DefinitionService:
    return DefinitionService(DefinitionRepository(db))


@router.post("/sources/", response_model=SourceDefinitionResponse)
def create_source_definition(
    name: str = Form(...),
    config_json: str | None = Form(None),
    logo_file: UploadFile | None = File(None),
    service: DefinitionService = Depends(get_definition_service),
    _admin: None = Depends(require_admin),
):
    source = SourceDefinitionCreate(name=name, config_json=parse_config_json(config_json))
    return service.create_source(source, logo_file)


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
    name: str | None = Form(None),
    config_json: str | None = Form(None),
    logo_file: UploadFile | None = File(None),
    service: DefinitionService = Depends(get_definition_service),
    _admin: None = Depends(require_admin),
):
    update_fields = {}
    if name:
        update_fields["name"] = name
    if config_json is not None:
        update_fields["config_json"] = parse_config_json(config_json)

    dto = SourceDefinitionUpdate(**update_fields)
    return service.update_source(source_id, dto, logo_file)


@router.delete("/sources/{source_id}")
def delete_source_definition(
    source_id: int,
    service: DefinitionService = Depends(get_definition_service),
    _admin : None = Depends(require_admin),
    
):
    service.delete_source(source_id)
    return {"message": "Source definition deleted successfully"}


@router.post("/destinations/", response_model=DestinationDefinitionResponse)
def create_destination_definition(
    service: DefinitionService = Depends(get_definition_service),
    name: str = Form(...),
    config_json: str | None = Form(None),
    logo_file: UploadFile | None = File(None),
    _admin: None = Depends(require_admin),
):
    destination = DestinationDefinitionCreate(name=name, config_json=parse_config_json(config_json))
    return service.create_destination(destination, logo_file)


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
    service: DefinitionService = Depends(get_definition_service),
    name: str | None = Form(None),
    config_json: str | None = Form(None),
    logo_file: UploadFile | None = File(None),
    _admin: None = Depends(require_admin),
):
    update_fields = {}
    if name:
        update_fields["name"] = name
    if config_json is not None:
        update_fields["config_json"] = parse_config_json(config_json)

    dto = DestinationDefinitionUpdate(**update_fields)
    return service.update_destination(destination_id, dto, logo_file)


@router.delete("/destinations/{destination_id}")
def delete_destination_definition(
    destination_id: int,
    service: DefinitionService = Depends(get_definition_service),
    _admin : None = Depends(require_admin),
    
):
    service.delete_destination(destination_id)
    return {"message": "Destination definition deleted successfully"}
