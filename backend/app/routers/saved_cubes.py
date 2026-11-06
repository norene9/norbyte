from fastapi import APIRouter, Depends

from app.core.security import get_current_user_db
from app.dependencies import get_saved_cube_service
from app.models import User
from app.schemas.saved_cube import SavedCubeCreate, SavedCubeResponse, SavedCubeUpdate
from app.services.saved_cube_service import SavedCubeService

router = APIRouter(prefix="/projects/{project_id}/cubes", tags=["saved-cubes"])


@router.post("/", response_model=SavedCubeResponse)
def create_cube(project_id: int, cube: SavedCubeCreate, current_user: User = Depends(get_current_user_db), service: SavedCubeService = Depends(get_saved_cube_service)):
    return service.create(project_id, current_user.id, cube)


@router.get("/", response_model=list[SavedCubeResponse])
def list_cubes(project_id: int, current_user: User = Depends(get_current_user_db), service: SavedCubeService = Depends(get_saved_cube_service)):
    return service.list(project_id, current_user.id)


@router.get("/{cube_id}", response_model=SavedCubeResponse)
def get_cube(project_id: int, cube_id: int, current_user: User = Depends(get_current_user_db), service: SavedCubeService = Depends(get_saved_cube_service)):
    return service.get(project_id, current_user.id, cube_id)


@router.put("/{cube_id}", response_model=SavedCubeResponse)
def update_cube(project_id: int, cube_id: int, cube: SavedCubeUpdate, current_user: User = Depends(get_current_user_db), service: SavedCubeService = Depends(get_saved_cube_service)):
    return service.update(project_id, current_user.id, cube_id, cube)


@router.delete("/{cube_id}")
def delete_cube(project_id: int, cube_id: int, current_user: User = Depends(get_current_user_db), service: SavedCubeService = Depends(get_saved_cube_service)):
    service.delete(project_id, current_user.id, cube_id)
    return {"message": "Saved cube deleted successfully"}


@router.post("/{cube_id}/refresh", response_model=SavedCubeResponse)
def refresh_cube(project_id: int, cube_id: int, current_user: User = Depends(get_current_user_db), service: SavedCubeService = Depends(get_saved_cube_service)):
    return service.refresh(project_id, current_user.id, cube_id)