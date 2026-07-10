from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class DestinationDefinition(Base):
    __tablename__ = "destination_definition"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    logo = Column(String, nullable=True)
    config_icon = Column(String, nullable=True)

    # Relationships
    connections = relationship("Connection", back_populates="destination_definition")
