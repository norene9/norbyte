
from pydantic import BaseModel
from typing import Any, Optional


class SourceDefinitionBase(BaseModel):
    name: str
    config_json: Optional[dict[str, Any]] = None
    connector_type: Optional[str] = None


class SourceDefinitionCreate(SourceDefinitionBase):
    pass


class SourceDefinitionResponse(SourceDefinitionBase):
    id: int
    logo: Optional[str] = None

    class Config:
        from_attributes = True


class SourceDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    config_json: Optional[dict[str, Any]] = None
    connector_type: Optional[str] = None
