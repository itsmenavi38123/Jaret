from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserPosAccess(BaseModel):
    user_id: str
    provider: str

    access_token: str
    refresh_token: Optional[str] = None

    expires_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str):
        allowed = {"square", "shopify", "clover", "lightspeed", "toast"}
        if v not in allowed:
            raise ValueError("Invalid provider")
        return v


class OauthState(BaseModel):
    state: str
    user_id: str
    provider: str
    expires_at: datetime

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str):
        allowed = {"square", "shopify", "clover", "lightspeed","toast"}
        if v not in allowed:
            raise ValueError("Invalid provider")
        return v