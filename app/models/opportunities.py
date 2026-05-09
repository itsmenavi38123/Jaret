# backend/app/models/opportunities.py

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class Opportunity(BaseModel):

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    opportunity_name: str
    category: str
    status: str  # e.g., "Tracked", "Selected", "Applied"
    deadline: Optional[datetime] = None
    expected_roi: float
    location_text: Optional[str] = None
    geo: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    opportunity_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class OpportunityCreate(BaseModel):
    opportunity_name: str
    category: str
    status: str
    deadline: Optional[datetime] = None
    expected_roi: float
    location_text: Optional[str] = None
    start_date: Optional[datetime] = None
    opportunity_type: Optional[str] = None


class OpportunityUpdate(BaseModel):

    opportunity_name: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    expected_roi: Optional[float] = None
    location_text: Optional[str] = None
    start_date: Optional[datetime] = None
    opportunity_type: Optional[str] = None