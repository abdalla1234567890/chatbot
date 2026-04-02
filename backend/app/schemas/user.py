from typing import Optional, List
from pydantic import BaseModel, field_validator
import re

SAUDI_MOBILE_REGEX = re.compile(r"^05\d{8}$")

# User
class UserBase(BaseModel):
    name: str
    phone: str
    is_admin: int = 0

    @field_validator("phone")
    @classmethod
    def validate_saudi_phone(cls, v: str) -> str:
        phone = (v or "").strip()
        if not SAUDI_MOBILE_REGEX.fullmatch(phone):
            raise ValueError("Phone must be 10 digits and start with 05")
        return phone

class UserCreate(UserBase):
    code: str

class UserUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_saudi_phone_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        phone = v.strip()
        if not SAUDI_MOBILE_REGEX.fullmatch(phone):
            raise ValueError("Phone must be 10 digits and start with 05")
        return phone

from app.schemas.location import Location as LocationSchema

class User(UserBase):
    code: str
    locations: List[LocationSchema] = []

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    code: str
