from pydantic import BaseModel
from typing import Optional, List


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    sync: bool = False


class ProjectCreate(ProjectBase):
    pass


class ConnectionResponse(BaseModel):
    id: int
    schedule: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    id: int
    connections: List[ConnectionResponse] = []

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sync: Optional[bool] = None
