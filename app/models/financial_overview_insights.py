from pydantic import BaseModel
from typing import List, Dict, Any


class ProfitabilityBanner(BaseModel):
    status: str
    message: str


class FinancialOverviewInsightItem(BaseModel):
    signal_id: str
    pressing_score: int

    state: str
    tier: str

    headline: str
    whats_going_on: str
    why_it_matters_now: str
    what_to_do: str
    expected_impact: str

    effort: str
    confidence: float

    directive: Dict[str, Any]

class FinancialOverviewInsights(BaseModel):
    profitability_banner: ProfitabilityBanner
    items: List[FinancialOverviewInsightItem]