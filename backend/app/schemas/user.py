from pydantic import BaseModel, EmailStr
from typing import List, Optional


class RoleBase(BaseModel):
    type: str


class RoleResponse(RoleBase):
    id: int
    

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = None
    


class UserResponse(UserBase):
    id: int
    role: RoleResponse 

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    
