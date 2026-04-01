from typing import List, Optional
from pydantic import BaseModel
from app.schemas.user import User

# Token
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[User] = None

# Chat
class ChatRequest(BaseModel):
    message: str
    history: List[str] = []

class ChatResponse(BaseModel):
    reply: str
    order_placed: bool = False

# Location
class LocationBase(BaseModel):
    name: str

class LocationCreate(LocationBase):
    pass

class Location(LocationBase):
    id: int

    class Config:
        from_attributes = True

class UserLocationsUpdate(BaseModel):
    location_ids: List[int]
