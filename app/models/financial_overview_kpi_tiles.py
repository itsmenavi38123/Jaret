# app/models/financial_overview_kpi_tiles.py

from pydantic import BaseModel
from typing import List


class FinancialOverviewKPITile(BaseModel):
    metric_id: str
    label: str
    value: str
    status: str
    forced_by_ai: bool = False
    is_pinned: bool = False


class FinancialOverviewKPITiles(BaseModel):
    items: List[FinancialOverviewKPITile]