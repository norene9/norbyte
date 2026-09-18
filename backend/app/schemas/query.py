from pydantic import BaseModel, Field


class MeasureRequest(BaseModel):
    field: str
    aggregation: str | None = None


class FilterRequest(BaseModel):
    field: str
    operator: str
    value: str | int | float | list[str | int | float]


class QueryRequest(BaseModel):
    table: str
    dimensions: list[str] = Field(default_factory=list)
    measures: list[MeasureRequest] = Field(default_factory=list)
    filters: list[FilterRequest] = Field(default_factory=list)
    joins: list[str] = Field(default_factory=list)
    limit: int = Field(default=1000, ge=1, le=50000)
