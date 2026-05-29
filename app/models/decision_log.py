from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class DecisionLog(BaseModel):

    user_id: str
    signal_id: Optional[str] = None
    signal_surface: Optional[str] = None
    action_title: str
    action_description: Optional[str] = None
    alternatives_considered: List[str] = Field(default_factory=list)
    consultation_sources: List[str] = Field(default_factory=list)
    owner_state: Optional[str] = None
    outcome_summary: Optional[str] = None
    outcome_metrics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)