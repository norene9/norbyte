from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base_class import Base


class SyncState(Base):
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connection.id"))
    table_name = Column(String, nullable=False)
    cursor_field = Column(String, nullable=True)
    cursor_value = Column(String, nullable=True)
