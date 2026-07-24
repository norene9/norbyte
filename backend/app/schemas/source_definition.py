from pydantic import BaseModel
from typing import Optional


class SourceDefinitionBase(BaseModel):
    name: str
    config_icon: Optional[str] = None


class SourceDefinitionCreate(SourceDefinitionBase):
    pass


class SourceDefinitionResponse(SourceDefinitionBase):
    id: int
    logo: Optional[str] = None 
    class Config:
        from_attributes = True


class SourceDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    config_icon: Optional[str] = None
