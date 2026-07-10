from http.client import HTTPException

from app.exceptions import BusinessRuleError, UserNotFoundError
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.core.security import verify_password

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def create(self, dto: UserCreate) -> User:
        if self.repository.get_by_username(dto.username):
            raise BusinessRuleError("Username already registered")
        return self.repository.create(dto)

    def get(self, user_id: int) -> User:
        user = self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return user

    def list(self) -> list[User]:
        return self.repository.list()

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.repository.get_by_username(username)
        if not user or not verify_password(plain_password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user
