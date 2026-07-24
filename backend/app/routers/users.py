from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import get_current_user_db, require_admin
from app.db.session import get_db
from app.repositories import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
from app.models import User
router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    service: UserService = Depends(get_user_service),
):
    return service.create(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    _admin: None = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return service.get(user_id)


@router.get("/", response_model=list[UserResponse])
def list_users(
    _admin: None = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return service.list()
@router.get("/current/user", response_model=UserResponse)
def get_current_(
    current_user: User = Depends(get_current_user_db),
    service: UserService = Depends(get_user_service),
):
    return service.get_me(current_user)
