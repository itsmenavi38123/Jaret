from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class XeroToken(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    tenant_id: str
    access_token: str
    refresh_token: str
    scope: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class XeroTokenCreate(BaseModel):
    user_id: str
    tenant_id: str
    access_token: str
    refresh_token: str
    scope: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int


class XeroTokenUpdate(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    updated_at: datetime
    is_active: Optional[bool] = None


class XeroTokenPublic(BaseModel):
    id: str
    user_id: str
    tenant_id: str
    token_type: str
    expires_in: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
