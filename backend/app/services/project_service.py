from app.exceptions import BusinessRuleError, ProjectNotFoundError
from app.models import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository

    def create(self, dto: ProjectCreate, user_id: int) -> Project:
        return self.repository.create(dto, user_id)

    def get(self, project_id: int, user_id: int | None = None) -> Project:
        project = self.repository.get_by_id(project_id, user_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return project

    def list(self, user_id: int | None = None) -> list[Project]:
        return self.repository.list(user_id)

    def update(self, project_id: int, dto: ProjectUpdate, user_id: int) -> Project:
        project = self.get(project_id, user_id)
        return self.repository.update(project, dto)

    def delete(self, project_id: int, user_id: int) -> None:
        project = self.get(project_id, user_id)
        self.repository.delete(project)
