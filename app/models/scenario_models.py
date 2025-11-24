# backend/app/models/scenario_models.py
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    """Request model for scenario planning"""
    query: str = Field(..., description="Free-text scenario query, e.g., 'Hire another HVAC tech at $65k'")
    business_context: Optional[Dict[str, Any]] = Field(None, description="Optional additional business context")


class Assumption(BaseModel):
    """Individual assumption with source"""
    key: str
    value: Any
    source: Optional[str] = None
    confidence: Optional[float] = None


class KPIs(BaseModel):
    """Financial KPIs for scenario"""
    roi: Optional[float] = Field(None, description="Return on Investment (%)")
    irr: Optional[float] = Field(None, description="Internal Rate of Return (%)")
    payback_years: Optional[float] = Field(None, description="Payback period in years")
    dscr: Optional[float] = Field(None, description="Debt Service Coverage Ratio")
    icr: Optional[float] = Field(None, description="Interest Coverage Ratio")
    runway_months: Optional[float] = Field(None, description="Cash runway in months")
    runway_delta_months: Optional[float] = Field(None, description="Change in runway vs baseline")
    cash_delta: Optional[float] = Field(None, description="Change in cash position")


class FinancialState(BaseModel):
    """Financial state snapshot"""
    cash: Optional[float] = None
    revenue: Optional[float] = None
    expenses: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    debt_service: Optional[float] = None
    interest_expense: Optional[float] = None
    monthly_burn: Optional[float] = None


class AdvisorRecommendation(BaseModel):
    """Advisor action item"""
    title: str
    impact: str
    priority: str = Field(..., description="high|medium|low")
    reason: str


class Advisor(BaseModel):
    """Advisor recommendations"""
    summary: str
    actions: List[AdvisorRecommendation]
    risks: List[Dict[str, str]]


class VisualData(BaseModel):
    """Chart data for frontend visualization"""
    type: str = Field(..., description="chart type: waterfall|tornado|cashflow|comparison")
    data: Dict[str, Any]


class ScenarioResponse(BaseModel):
    """Response model for scenario planning"""
    query: str
    scenario_type: str = Field(..., description="Detected scenario type: CapEx|Hiring|Pricing|Expansion|Other")
    assumptions: List[Assumption] = Field(default_factory=list, description="Assumptions used with sources")
    used_priors: bool = Field(True, description="Whether Research Scout filled missing priors")
    baseline: FinancialState
    projected: FinancialState
    kpis: KPIs
    advisor: Advisor
    visuals: List[VisualData] = Field(default_factory=list)
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Provenance for assumptions")
    explain_math: Optional[str] = Field(None, description="Detailed calculation explanation")
    why_it_matters: Optional[str] = Field(None, description="Business impact explanation")
