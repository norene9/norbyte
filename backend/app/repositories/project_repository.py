from sqlalchemy.orm import Session
from app.models import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, dto: ProjectCreate) -> Project:
        project = Project(**dto.model_dump())
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_by_id(self, project_id: int):
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list(self) -> list[Project]:
        return self.db.query(Project).all()

    def update(self, project: Project, dto: ProjectUpdate) -> Project:
        update_data = dto.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)

        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()
