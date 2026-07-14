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
    is_beta: bool = False
    needs_password_setup: bool = False
    is_admin: bool = False  # Dedicated platform-admin flag; never settable via any API, DB-provisioned only
    totp_enrolled: bool = False
    totp_secret: Optional[str] = None
    totp_pending_secret: Optional[str] = None
    created_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
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
