from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Connection(Base):
    __tablename__ = "connection"

    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(Integer, ForeignKey("destination_definition.id"))
    source_id = Column(Integer, ForeignKey("source_definition.id"))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    schedule = Column(String, nullable=True)
    last_scheduled_at = Column(String, nullable=True)
    source_connection_json = Column(String, nullable=False)
    destination_connection_json = Column(String, nullable=False)
    selected_streams = Column(JSON, nullable=True)
    destination_table_prefix = Column(String, nullable=True)

    # Relationships
    destination_definition = relationship("DestinationDefinition", back_populates="connections")
    source_definition = relationship("SourceDefinition", back_populates="connections")
    project = relationship("Project", back_populates="connections")
    schemas = relationship("Schema", back_populates="connection")
    sync_jobs = relationship("SyncJob", back_populates="connection")
