# backend/app/models/opportunities.py

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


class Opportunity(BaseModel):

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str
    opportunity_name: str
    category: str
    status: str
    deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    status_user: Optional[str] = None
    normalized_title: Optional[str] = None
    expected_roi: float
    location_text: Optional[str] = None
    geo: Optional[Dict[str, Any]] = None
    distance_miles: Optional[float] = None
    drive_time_minutes: Optional[int] = None
    drive_time_estimate: Optional[str] = None
    drive_time_is_estimated: bool = False
    opportunity_type: Optional[str] = None
    source_name: Optional[str] = None
    box_type: Optional[str] = None
    asset_used: Optional[str] = None

    # Registration fields (4+ fields inside dict)
    registration_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )

    # Example:
    # {
    #     "registration_url": "",
    #     "registration_guidance": "",
    #     "listed_contract_value": "",
    #     "notes": ""
    # }

    # Scoring fields (10+ fields inside dict)
    scoring_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )

    # Example:
    # {
    #     "match_score": 0,
    #     "readiness_score": 0,
    #     "event_readiness_score": 0,
    #     "preliminary_fit_score": 0,
    #     "original_preliminary_fit_score": 0,
    #     "industry_capability_match": 0,
    #     "geographic_fit": 0,
    #     "timing_fit": 0,
    #     "affordability_score": 0,
    #     "confidence_penalty": 0
    # }

    # Verification fields (10+ fields inside dict)
    verification_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )

    # Example:
    # {
    #     "has_prior_participation": false,
    #     "years_running": 0,
    #     "prior_event_verifiable": false,
    #     "organizer_web_presence": "",
    #     "press_coverage_found": false,
    #     "credibility_summary": "",
    #     "data_trust_indicator": "",
    #     "scam_signal_count": 0,
    #     "verify_flag": false,
    #     "verify_flag_message": ""
    # }

    # Weather fields (5+ fields inside dict)
    weather_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )

    # Example:
    # {
    #     "weather_snapshot": {},
    #     "weather_risk_detected": false,
    #     "weather_risk_message": "",
    #     "temperature_max_f": 0,
    #     "weather_badge": ""
    # }

    # Risk fields (5+ fields inside dict)
    risk_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )

    # Example:
    # {
    #     "risk_signals": [],
    #     "scam_signals": [],
    #     "why_reason_codes": [],
    #     "score_history": [],
    #     "extraction_confidence": 0
    # }

    # Event metadata fields (5+ fields inside dict)
    event_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )

    # Example:
    # {
    #     "event_prestige_tier": "",
    #     "event_audience": "",
    #     "event_service_fit": [],
    #     "type_specific": {},
    #     "buzz_signals": {}
    # }

    # Portfolio fields (3+ fields inside dict)
    portfolio_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )

    # Example:
    # {
    #     "portfolio_adjusted_readiness": 0,
    #     "status_user": "None",
    #     "last_scored_at": null
    # }

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