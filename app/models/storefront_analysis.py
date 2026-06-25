from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StorefrontObservation(BaseModel):
    category: str
    observation: str
    confidence: str = "medium"
    basis: List[str] = Field(default_factory=list)


class LocationVitalityObservation(BaseModel):
    observation: str
    confidence: str = "medium"
    basis: List[str] = Field(default_factory=list)


class StorefrontAnalysis(BaseModel):
    user_id: str
    location_id: Optional[str] = None

    storefront_observations: List[StorefrontObservation] = Field(
        default_factory=list
    )

    location_vitality_observations: List[LocationVitalityObservation] = Field(
        default_factory=list
    )

    raw_vision_output: Dict[str, Any] = Field(
        default_factory=dict
    )

    raw_reasoning_output: Dict[str, Any] = Field(
        default_factory=dict
    )