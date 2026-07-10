from sqlalchemy.orm import Session
from app.models import User
from app.schemas.user import UserCreate
from app.core.security import hash_password


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, dto: UserCreate) -> User:
        user_data = dto.model_dump()
        user_data["password"] = hash_password(user_data["password"])
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()

    def list(self) -> list[User]:
        return self.db.query(User).all()
