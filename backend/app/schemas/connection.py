from pydantic import BaseModel
from typing import Optional, Dict, Any


class ConnectionBase(BaseModel):
    destination_id: int
    source_id: int
    project_id: int
    schedule: Optional[str] = None
    source_connection_json: Optional[Dict[str, Any]] = None
    destination_connection_json: Optional[Dict[str, Any]] = None


class ConnectionCreate(ConnectionBase):
    pass


class SchemaResponse(BaseModel):
    id: int
    schedule: Optional[str] = None
    version: Optional[str] = None

    class Config:
        from_attributes = True


class DestinationDefinitionResponse(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None

    class Config:
        from_attributes = True


class SourceDefinitionResponse(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None

    class Config:
        from_attributes = True


class ConnectionResponse(ConnectionBase):
    id: int
    destination_definition: Optional[DestinationDefinitionResponse] = None
    source_definition: Optional[SourceDefinitionResponse] = None
    schemas: list[SchemaResponse] = []

    class Config:
        from_attributes = True


class ConnectionUpdate(BaseModel):
    schedule: Optional[str] = None
    source_connection_json: Optional[Dict[str, Any]] = None
    destination_connection_json: Optional[Dict[str, Any]] = None
