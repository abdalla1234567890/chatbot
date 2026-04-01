from pydantic import BaseModel
from typing import List, Optional

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
