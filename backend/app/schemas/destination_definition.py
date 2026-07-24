from pydantic import BaseModel
from typing import Optional


class DestinationDefinitionBase(BaseModel):
    name: str
    config_icon: Optional[str] = None


class DestinationDefinitionCreate(DestinationDefinitionBase):
    pass


class DestinationDefinitionResponse(DestinationDefinitionBase):
    id: int

    class Config:
        from_attributes = True


class DestinationDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    config_icon: Optional[str] = None
