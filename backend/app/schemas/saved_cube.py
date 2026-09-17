from pydantic import BaseModel, ConfigDict, Field

from app.schemas.query import QueryRequest


class SavedCubeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query_definition: QueryRequest
    output_table: str | None = Field(default=None, max_length=120)
    refresh_schedule: str | None = None


class SavedCubeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    query_definition: QueryRequest | None = None
    output_table: str | None = Field(default=None, max_length=120)
    refresh_schedule: str | None = None


class SavedCubeResponse(BaseModel):
    id: int
    project_id: int
    name: str
    query_definition: QueryRequest
    output_table: str
    refresh_schedule: str | None = None
    last_refreshed_at: str | None = None

    model_config = ConfigDict(from_attributes=True)