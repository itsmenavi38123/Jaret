from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional

class BetaCohort(str, Enum):
    internal = "internal"
    friends_trusted = "friends_trusted"
    advisors = "advisors"
    external_beta = "external_beta"

class BetaStatus(str, Enum):
    invited = "invited"
    accepted = "accepted"
    onboarded = "onboarded"
    active = "active"
    inactive = "inactive"

class BetaProfile(BaseModel):
    user_id: str
    is_beta: bool = False
    beta_cohort: Optional[BetaCohort] = None
    beta_status: Optional[BetaStatus] = None
    nda_required: bool = False
    beta_notes: Optional[str] = None
    beta_updated_at: Optional[datetime] = None
    beta_updated_by: Optional[str] = None