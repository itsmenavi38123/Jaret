from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class QuickBooksToken(BaseModel):
    id: str = Field(alias="_id")
    user_id: str  
    realm_id: str 
    access_token: str
    refresh_token: str
    id_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int 
    x_refresh_token_expires_in: int 
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class QuickBooksTokenCreate(BaseModel):
    user_id: str
    realm_id: str
    access_token: str
    refresh_token: str
    id_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    x_refresh_token_expires_in: int

class QuickBooksTokenUpdate(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    expires_in: Optional[int] = None
    x_refresh_token_expires_in: Optional[int] = None
    updated_at: datetime
    is_active: Optional[bool] = None

class QuickBooksTokenPublic(BaseModel):
    id: str
    user_id: str
    realm_id: str
    token_type: str
    expires_in: int
    x_refresh_token_expires_in: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }