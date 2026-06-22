from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class ProfitabilityBanner(BaseModel):
    status: Optional[str] = None
    headline: str = ""
    supporting_text: str = ""
    missing_data_notice: Optional[str] = None


class FinancialOverviewInsightItem(BaseModel):
    signal_id: str
    pressing_score: int
    tier: str
    headline: str
    whats_going_on: str
    why_it_matters_now: str
    what_to_do: str
    expected_impact: Dict[str, Any]
    effort: str
    confidence: str

    directive: Dict[str, Any]

class FinancialOverviewInsights(BaseModel):
    profitability_banner: ProfitabilityBanner
    items: List[FinancialOverviewInsightItem]
    missing_data_notice: Optional[str] = None