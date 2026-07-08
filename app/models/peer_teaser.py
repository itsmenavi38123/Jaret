from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid

class PeerTeaser(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        alias="_id"
    )
    source_customer_id: str
    verified_anonymized: bool = True
    status: str = "review"  # "review", "approved", "rejected", "retired"
    teaser_text: str
    onboarding_section: Optional[str] = "Financials"
    proposed_by: Optional[str] = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("verified_anonymized")
    @classmethod
    def validate_verified_anonymized(cls, v: bool):
        if not v:
            raise ValueError("Every teaser row must have verified_anonymized: true")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str):
        allowed = {"review", "approved", "rejected", "retired"}
        if v not in allowed:
            raise ValueError("Status must be review, approved, rejected, or retired")
        return v

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class PeerTeaserCreate(BaseModel):
    source_customer_id: str
    verified_anonymized: bool = True
    teaser_text: str
    status: Optional[str] = "approved"
    onboarding_section: Optional[str] = "Financials"
    proposed_by: Optional[str] = "manual"

    @field_validator("verified_anonymized")
    @classmethod
    def validate_verified_anonymized(cls, v: bool):
        if not v:
            raise ValueError("Every teaser row must have verified_anonymized: true")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str):
        allowed = {"review", "approved", "rejected", "retired"}
        if v not in allowed:
            raise ValueError("Status must be review, approved, rejected, or retired")
        return v

class PeerTeaserUpdate(BaseModel):
    teaser_text: Optional[str] = None
    status: Optional[str] = None
    verified_anonymized: Optional[bool] = None
    onboarding_section: Optional[str] = None
    proposed_by: Optional[str] = None

    @field_validator("verified_anonymized")
    @classmethod
    def validate_verified_anonymized(cls, v: Optional[bool]):
        if v is not None and not v:
            raise ValueError("Every teaser row must have verified_anonymized: true")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]):
        if v is not None:
            allowed = {"review", "approved", "rejected", "retired"}
            if v not in allowed:
                raise ValueError("Status must be review, approved, rejected, or retired")
        return v
