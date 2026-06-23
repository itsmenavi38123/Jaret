from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FinancialOverviewDrawerContext(BaseModel):
    financial_overview: Optional[Any] = None
    benchmarks: Optional[Any] = None


class FinancialOverviewDrawerRequest(BaseModel):
    kpi_name: str
    current_value: Optional[float] = None
    prior_value: Optional[float] = None
    format_type: str
    already_displayed_insights: list = []
    optional_context: Optional[
        FinancialOverviewDrawerContext
    ] = None


class FinancialOverviewAskAIRequest(BaseModel):
    kpi_name: str
    current_value: Optional[float] = None
    prior_value: Optional[float] = None
    question: str
    chat_history: Optional[
        List[Dict[str, str]]
    ] = []
    optional_context: Optional[
        Dict[str, Any]
    ] = None
    already_displayed_insights: Optional[
        List[Dict[str, Any]]
    ] = []