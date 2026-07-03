from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(ProjectRepository(db))


@router.post("/", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
):
    return service.create(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
):
    return service.get(project_id)


@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    service: ProjectService = Depends(get_project_service),
):
    return service.list()


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
):
    return service.update(project_id, project)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
):
    service.delete(project_id)
    return {"message": "Project deleted successfully"}
