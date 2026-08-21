from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class KPIDriverItem(BaseModel):
    number: int
    headline: str
    category: str
    impact_value: str


class FinancialOverviewKPITile(BaseModel):
    metric_id: str
    label: str
    value: str
    status: str
    forced_by_ai: bool = False
    is_pinned: bool = False
    change_text: Optional[str] = None
    trend: Optional[List[float]] = None
    verdict: Optional[str] = None
    change_indicator: Optional[str] = None
    drivers: Optional[List[KPIDriverItem]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    confidence_footer: Optional[str] = None


class FinancialOverviewKPITiles(BaseModel):
    items: List[FinancialOverviewKPITile]