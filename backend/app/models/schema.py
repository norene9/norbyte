from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Schema(Base):
    __tablename__ = "schema"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connection.id"))
    schedule = Column(String, nullable=True)
    streams_json = Column(JSON, nullable=True)
    version = Column(String, nullable=True)

    # Relationships
    connection = relationship("Connection", back_populates="schemas")
