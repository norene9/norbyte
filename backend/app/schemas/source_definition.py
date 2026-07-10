from pydantic import BaseModel
from typing import Optional


class SourceDefinitionBase(BaseModel):
    name: str
    logo: Optional[str] = None
    config_icon: Optional[str] = None


class SourceDefinitionCreate(SourceDefinitionBase):
    pass


class SourceDefinitionResponse(SourceDefinitionBase):
    id: int

    class Config:
        from_attributes = True


class SourceDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None
    config_icon: Optional[str] = None
