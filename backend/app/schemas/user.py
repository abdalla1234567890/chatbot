from typing import Optional, List
from pydantic import BaseModel

# User
class UserBase(BaseModel):
    name: str
    phone: str
    is_admin: int = 0

class UserCreate(UserBase):
    code: str

class UserUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None

from app.schemas.location import Location as LocationSchema

class User(UserBase):
    code: str
    locations: List[LocationSchema] = []

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    code: str
