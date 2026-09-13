from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.connectors.registry import get_destination_connector
from app.core.encryption import decrypt_config
from app.core.security import get_current_user_db
from app.db.session import get_db
from app.models import Connection, User
from app.repositories import ProjectRepository
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.definition_repository import DefinitionRepository
from app.repositories.semantic_repository import SemanticRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.query import QueryRequest
from app.services.project_service import ProjectService
from app.services.query_engine import QueryEngine
from app.dependencies import get_query_engine

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(ProjectRepository(db))


@router.post("/", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user_db),
    service: ProjectService = Depends(get_project_service),
):
    return service.create(project, current_user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user_db),
    service: ProjectService = Depends(get_project_service),
):
    return service.get(project_id, current_user.id)


@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    current_user: User = Depends(get_current_user_db),
    service: ProjectService = Depends(get_project_service),
):
    return service.list(current_user.id)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project: ProjectUpdate,
    current_user: User = Depends(get_current_user_db),
    service: ProjectService = Depends(get_project_service),
):
    return service.update(project_id, project, current_user.id)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user_db),
    service: ProjectService = Depends(get_project_service),
):
    service.delete(project_id, current_user.id)
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/query")
def run_project_query(
    project_id: int,
    request: QueryRequest,
    current_user: User = Depends(get_current_user_db),
    engine: QueryEngine = Depends(get_query_engine),
    db: Session = Depends(get_db),
):
    project_service = ProjectService(ProjectRepository(db))
    project_service.get(project_id, current_user.id)

    sql, params = engine.build(project_id, request)

    connection = (
        db.query(Connection)
        .filter(Connection.project_id == project_id)
        .order_by(Connection.id.asc())
        .first()
    )
    if not connection:
        raise HTTPException(status_code=404, detail="No connection found for project")

    destination_definition = DefinitionRepository(db).get_destination_by_id(connection.destination_id)
    if not destination_definition:
        raise HTTPException(status_code=404, detail="Destination definition not found")

    connector_cls = get_destination_connector(destination_definition.connector_type)
    connector = connector_cls(decrypt_config(connection.destination_connection_json))
    conn = connector._connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            return {"columns": columns, "rows": rows}
    finally:
        conn.close()
