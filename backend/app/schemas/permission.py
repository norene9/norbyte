from pydantic import BaseModel
from typing import Optional


class PermissionBase(BaseModel):
    action: str
    model: str


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: int

    class Config:
        from_attributes = True


class PermissionUpdate(BaseModel):
    action: Optional[str] = None
    model: Optional[str] = None
