from pydantic import BaseModel, ConfigDict, Field


class SemanticFieldCreate(BaseModel):
    column_name: str
    display_name: str
    field_type: str
    data_type: str
    default_aggregation: str | None = None
    is_hidden: bool = False


class SemanticFieldResponse(SemanticFieldCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SemanticTableCreate(BaseModel):
    project_id: int
    connection_id: int
    physical_table: str
    display_name: str
    description: str | None = None
    fields: list[SemanticFieldCreate] = Field(default_factory=list)


class SemanticTableResponse(BaseModel):
    id: int
    project_id: int
    connection_id: int
    physical_table: str
    display_name: str
    description: str | None = None
    fields: list[SemanticFieldResponse]
    model_config = ConfigDict(from_attributes=True)


class SemanticRelationshipCreate(BaseModel):
    project_id: int
    name: str
    from_table_id: int
    from_column: str
    to_table_id: int
    to_column: str
    relationship_type: str = "many_to_one"


class SemanticRelationshipResponse(SemanticRelationshipCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)