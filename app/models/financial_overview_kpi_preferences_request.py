from typing import List

from pydantic import BaseModel


class FinancialOverviewKPIPreferencesRequest(
    BaseModel
):
    hidden_metric_ids: List[str] = []
    pinned_metric_ids: List[str] = []
    tile_order: List[str] = []
    