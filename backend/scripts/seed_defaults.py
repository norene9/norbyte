import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal, initialize_database
from app.models import Role, User

DEFAULT_ROLE_TYPES = ("admin", "user")
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "b1sra7w1toh")


def seed_defaults(db: Session | None = None) -> dict[str, object]:
    if db is None:
        initialize_database()
        db = SessionLocal()

    created_roles: list[str] = []
    for role_type in DEFAULT_ROLE_TYPES:
        role = db.query(Role).filter(Role.type == role_type).first()
        if not role:
            role = Role(type=role_type)
            db.add(role)
            created_roles.append(role_type)

    db.flush()
    admin_role = db.query(Role).filter(Role.type == "admin").first()
    user_role = db.query(Role).filter(Role.type == "user").first()
    admin_user = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
    if not admin_user:
        admin_user = User(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            password=DEFAULT_ADMIN_PASSWORD,
            role_id=admin_role.id if admin_role else None
            
        )
        db.add(admin_user)
        db.flush()

    

    db.commit()
    return {
        "roles_created": created_roles,
        "admin_user_created": DEFAULT_ADMIN_USERNAME,
    }


if __name__ == "__main__":
    result = seed_defaults()
    print(result)
