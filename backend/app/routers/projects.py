from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import get_current_user_db
from app.db.session import get_db
from app.models import User
from app.repositories import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

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
