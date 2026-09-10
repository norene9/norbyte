from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user_db
from app.db.session import get_db
from app.dependencies import get_semantic_service
from app.models import User
from app.schemas.semantic import (
    SemanticRelationshipCreate,
    SemanticRelationshipResponse,
    SemanticRelationshipUpdate,
    SemanticTableCreate,
    SemanticTableResponse,
    SemanticTableUpdate,
)
from app.services.semantic_service import SemanticService


router = APIRouter(prefix="/semantic", tags=["semantic"])


@router.post("/tables", response_model=SemanticTableResponse)
def create_semantic_table(
    dto: SemanticTableCreate,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    return service.create_table(dto)


@router.put("/tables/{table_id}", response_model=SemanticTableResponse)
def update_semantic_table(
    table_id: int,
    dto: SemanticTableUpdate,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    return service.update_table(table_id, dto)


@router.delete("/tables/{table_id}")
def delete_semantic_table(
    table_id: int,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    service.delete_table(table_id)
    return {"message": "Semantic table deleted successfully"}


@router.get("/tables/suggest")
def suggest_semantic_table(
    connection_id: int,
    table: str,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    return service.suggest_fields(connection_id, table)


@router.get("/projects/{project_id}/tables", response_model=list[SemanticTableResponse])
def list_semantic_tables(
    project_id: int,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    return service.list_tables(project_id)


@router.post("/relationships", response_model=SemanticRelationshipResponse)
def create_relationship(
    dto: SemanticRelationshipCreate,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    return service.create_relationship(dto)


@router.put("/relationships/{relationship_id}", response_model=SemanticRelationshipResponse)
def update_relationship(
    relationship_id: int,
    dto: SemanticRelationshipUpdate,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    return service.update_relationship(relationship_id, dto)


@router.delete("/relationships/{relationship_id}")
def delete_relationship(
    relationship_id: int,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    service.delete_relationship(relationship_id)
    return {"message": "Semantic relationship deleted successfully"}


@router.get("/projects/{project_id}/relationships", response_model=list[SemanticRelationshipResponse])
def list_relationships(
    project_id: int,
    current_user: User = Depends(get_current_user_db),
    service: SemanticService = Depends(get_semantic_service),
):
    return service.list_relationships(project_id)