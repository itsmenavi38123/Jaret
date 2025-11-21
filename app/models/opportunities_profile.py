# backend/app/models/opportunities_profile.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class OpportunitiesProfile(BaseModel):
    user_id: str
    business_type: str
    operating_region: str
    preferred_opportunity_types: List[str]  # List of strings from: RFPs & Bids, Grants, Trade Shows & Events, Partnerships, Vendor/Subcontractor, Certifications/Training
    radius: int
    max_budget: float
    travel_range: str
    staffing_capacity: int
    risk_appetite: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class OpportunitiesProfileCreate(BaseModel):
    business_type: str
    operating_region: str
    preferred_opportunity_types: List[str]
    radius: int
    max_budget: float
    travel_range: str
    staffing_capacity: int
    risk_appetite: str

class OpportunitiesProfileUpdate(BaseModel):
    business_type: Optional[str] = None
    operating_region: Optional[str] = None
    preferred_opportunity_types: Optional[List[str]] = None
    radius: Optional[int] = None
    max_budget: Optional[float] = None
    travel_range: Optional[str] = None
    staffing_capacity: Optional[int] = None
    risk_appetite: Optional[str] = None