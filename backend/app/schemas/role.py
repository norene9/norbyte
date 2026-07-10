from pydantic import BaseModel
from typing import Optional


class RoleBase(BaseModel):
    type: str


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id: int

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    type: Optional[str] = None
