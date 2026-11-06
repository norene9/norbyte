from sqlalchemy.orm import Session

from app.models import SavedCube
from app.schemas.saved_cube import SavedCubeCreate, SavedCubeUpdate


class SavedCubeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, project_id: int, data: dict) -> SavedCube:
        cube = SavedCube(project_id=project_id, **data)
        self.db.add(cube)
        self.db.commit()
        self.db.refresh(cube)
        return cube

    def get(self, cube_id: int, project_id: int) -> SavedCube | None:
        return (
            self.db.query(SavedCube)
            .filter(SavedCube.id == cube_id, SavedCube.project_id == project_id)
            .first()
        )

    def list(self, project_id: int) -> list[SavedCube]:
        return self.db.query(SavedCube).filter(SavedCube.project_id == project_id).order_by(SavedCube.id).all()

    def update(self, cube: SavedCube, dto: SavedCubeUpdate) -> SavedCube:
        for key, value in dto.model_dump(exclude_unset=True).items():
            if hasattr(value, "model_dump"):
                value = value.model_dump()
            setattr(cube, key, value)
        self.db.add(cube)
        self.db.commit()
        self.db.refresh(cube)
        return cube

    def delete(self, cube: SavedCube) -> None:
        self.db.delete(cube)
        self.db.commit()