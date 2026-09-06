from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class SemanticTable(Base):
    __tablename__ = "semantic_table"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    connection_id = Column(Integer, ForeignKey("connection.id"), nullable=False, index=True)
    physical_table = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    fields = relationship("SemanticField", back_populates="table", cascade="all, delete-orphan")


class SemanticField(Base):
    __tablename__ = "semantic_field"

    id = Column(Integer, primary_key=True, index=True)
    semantic_table_id = Column(Integer, ForeignKey("semantic_table.id"), nullable=False, index=True)
    column_name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    default_aggregation = Column(String, nullable=True)
    is_hidden = Column(Boolean, default=False, nullable=False)

    table = relationship("SemanticTable", back_populates="fields")


class SemanticRelationship(Base):
    __tablename__ = "semantic_relationship"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    from_table_id = Column(Integer, ForeignKey("semantic_table.id"), nullable=False)
    from_column = Column(String, nullable=False)
    to_table_id = Column(Integer, ForeignKey("semantic_table.id"), nullable=False)
    to_column = Column(String, nullable=False)
    relationship_type = Column(String, nullable=False, default="many_to_one")