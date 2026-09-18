from sqlalchemy import Column, Integer, String, ForeignKey, Text
from  sqlalchemy.orm import relationship
from app.db.base_class import Base
class SyncJob(Base):
    __tablename__ = "sync_job"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connection.id"))
    status = Column(String, nullable=False)
    started_at = Column(String, nullable=True)
    records_processed = Column(Integer, nullable=True)
    finished_at = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    logs = Column(Text, nullable=True)

    # Relationships
    connection = relationship("Connection", back_populates="sync_jobs")