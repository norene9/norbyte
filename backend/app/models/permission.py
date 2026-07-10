from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, index=True)
    model = Column(String, index=True)

    # Relationships
    roles = relationship("Role", secondary="role_permission_association", back_populates="permissions")
