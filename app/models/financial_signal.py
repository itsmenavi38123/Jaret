from typing import Optional

from pydantic import BaseModel


class FinancialSignal(BaseModel):
    signal_id: str
    title: str
    state: str
    pressing_score: int
    shape_id: str
    severity: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    recommended_action: Optional[str] = None
    headline: Optional[str] = None
    whats_going_on: Optional[str] = None
    why_it_matters_now: Optional[str] = None
    what_to_do: Optional[str] = None
    expected_impact: Optional[str] = None
    effort: Optional[str] = None
    confidence: Optional[float] = None