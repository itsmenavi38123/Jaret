from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class FacebookToken(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    page_id: str
    page_name: Optional[str] = None
    access_token: str
    token_type: str = "bearer"
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class FacebookTokenCreate(BaseModel):
    user_id: str
    page_id: str
    page_name: Optional[str] = None
    access_token: str
    token_type: str = "bearer"
    expires_at: Optional[datetime] = None

class FacebookTokenUpdate(BaseModel):
    access_token: Optional[str] = None
    page_name: Optional[str] = None
    expires_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: Optional[bool] = None
