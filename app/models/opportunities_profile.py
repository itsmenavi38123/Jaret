# backend/app/models/opportunities_profile.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class OpportunitiesProfile(BaseModel):
    user_id: str
    business_type: str
    operating_region: str
    preferred_opportunity_types: List[str]
    radius: int
    max_budget: float
    travel_range: str
    staffing_capacity: int
    risk_appetite: str
    service_model: Optional[str] = None
    price_tier: Optional[str] = None
    audience: Optional[str] = None
    proven_capabilities: List[str] = Field(default_factory=list)
    historical_outcomes: List[dict] = Field( default_factory=list)
    auto_sync: bool = True
    indoor_only: bool = False
    cash_balance: Optional[float] = 0
    outstanding_ar: List[dict] = Field(default_factory=list)
    runway_trend: Optional[str] = "stable"

    demand_strain_next_30d: Optional[float] = None
    demand_strain_next_60d: Optional[float] = None
    demand_strain_next_90d: Optional[float] = None

    permits_and_licenses: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
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

    service_model: Optional[str] = None
    price_tier: Optional[str] = None
    audience: Optional[str] = None

    proven_capabilities: List[str] = Field(default_factory=list)
    historical_outcomes: List[dict] = Field(default_factory=list)

    cash_balance: Optional[float] = 0
    outstanding_ar: List[dict] = Field(default_factory=list)
    runway_trend: Optional[str] = "stable"

    demand_strain_next_30d: Optional[float] = None
    demand_strain_next_60d: Optional[float] = None
    demand_strain_next_90d: Optional[float] = None

    permits_and_licenses: List[str] = Field(default_factory=list)
    auto_sync: bool = True
    indoor_only: bool = False


class OpportunitiesProfileUpdate(BaseModel):
    business_type: Optional[str] = None
    operating_region: Optional[str] = None
    preferred_opportunity_types: Optional[List[str]] = None
    radius: Optional[int] = None
    max_budget: Optional[float] = None
    travel_range: Optional[str] = None
    staffing_capacity: Optional[int] = None
    risk_appetite: Optional[str] = None

    service_model: Optional[str] = None
    price_tier: Optional[str] = None
    audience: Optional[str] = None

    proven_capabilities: Optional[List[str]] = None
    historical_outcomes: Optional[List[dict]] = None

    cash_balance: Optional[float] = None
    outstanding_ar: Optional[List[dict]] = None
    runway_trend: Optional[str] = None

    demand_strain_next_30d: Optional[float] = None
    demand_strain_next_60d: Optional[float] = None
    demand_strain_next_90d: Optional[float] = None

    permits_and_licenses: Optional[List[str]] = None

    auto_sync: Optional[bool] = None
    indoor_only: Optional[bool] = None