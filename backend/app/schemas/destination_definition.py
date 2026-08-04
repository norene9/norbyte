from typing import Any, Optional

from pydantic import BaseModel


class DestinationDefinitionBase(BaseModel):
    name: str
    config_json: Optional[dict[str, Any]] = None


class DestinationDefinitionCreate(DestinationDefinitionBase):
    pass


class DestinationDefinitionResponse(DestinationDefinitionBase):
    id: int
    logo: Optional[str] = None

    class Config:
        from_attributes = True


class DestinationDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    config_json: Optional[dict[str, Any]] = None
