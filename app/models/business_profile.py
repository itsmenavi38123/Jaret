# backend/app/models/business_profile.py
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class BusinessProfile(BaseModel):
    user_id: str
    onboarding_data: Dict[str, Any]  # Nested dict for questions and answers
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class BusinessProfileCreate(BaseModel):
    onboarding_data: Dict[str, Any]

class BusinessProfileUpdate(BaseModel):
    onboarding_data: Dict[str, Any]