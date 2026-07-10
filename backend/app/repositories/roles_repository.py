from sqlalchemy.orm import Session
from app.models import Role

class RolesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_role(self, role_id: int):
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_roles(self):
        return self.db.query(Role).all()
