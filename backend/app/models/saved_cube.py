from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class SavedCube(Base):
    __tablename__ = "saved_cube"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    query_definition = Column(JSONB, nullable=False)
    output_table = Column(String, nullable=False, unique=True)
    refresh_schedule = Column(String, nullable=True)
    last_refreshed_at = Column(String, nullable=True)

    project = relationship("Project", back_populates="saved_cubes")