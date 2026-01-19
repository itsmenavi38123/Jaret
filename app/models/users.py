# backend/app/models/user.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserInDB(BaseModel):
    id: str = Field(alias="_id")
    email: EmailStr
    password_hash: str
    full_name: str
    company_name: str
    is_verified: bool = False
    is_paused: bool = False  # Admin can pause/unpause accounts
    last_active: Optional[datetime] = None
    role: str = "Viewer"  # Owner | Admin | Viewer
    signup_source: str = "demo"  # demo | invite
    created_at: datetime

    class Config:
        populate_by_name = True
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

# Input schema for signup (request body)
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


# Input schema for login (request body)
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Output schema (for responses)
class UserPublic(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime
