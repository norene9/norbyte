from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

# Association table for many-to-many relationship
role_permission_association = Table(
    'role_permission_association',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('role.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, unique=True, index=True)

    # Relationships
    users = relationship("User", secondary="user_role_association", back_populates="roles")
    permissions = relationship("Permission", secondary=role_permission_association, back_populates="roles")
