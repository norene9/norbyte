from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    sync = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="projects")
    connections = relationship("Connection", back_populates="project")
    saved_cubes = relationship("SavedCube", back_populates="project", cascade="all, delete-orphan")
