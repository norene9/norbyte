from pydantic import BaseModel
from typing import List, Optional


class PermissionBase(BaseModel):
    action: str
    model: str


class PermissionResponse(PermissionBase):
    id: int

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    type: str


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id: int
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    type: Optional[str] = None
