from pydantic import BaseModel
from typing import Optional, Dict, Any


class SchemaBase(BaseModel):
    connection_id: int
    schedule: Optional[str] = None
    streams_json: Optional[Dict[str, Any]] = None
    version: Optional[str] = None


class SchemaCreate(SchemaBase):
    pass


class SchemaResponse(SchemaBase):
    id: int

    class Config:
        from_attributes = True


class SchemaUpdate(BaseModel):
    schedule: Optional[str] = None
    streams_json: Optional[Dict[str, Any]] = None
    version: Optional[str] = None
