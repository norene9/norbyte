from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.security import clear_session_cookies, get_current_user, rotate_refresh_token, set_session_cookies
from app.db.session import get_db
from app.repositories import UserRepository
from app.schemas.user import UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    service: UserService = Depends(get_user_service),
):
    user = service.authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    set_session_cookies(response, user.id, user.role.type if user.role else "")
    return {"message": "Logged in successfully", "user": UserResponse.model_validate(user).model_dump()}


@router.post("/refresh")
def refresh(response: Response, request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    rotate_refresh_token(response, refresh_token)
    return {"message": "Tokens rotated successfully"}


@router.post("/logout")
def logout(response: Response):
    clear_session_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me")
def me(request: Request):
    return get_current_user(request)
