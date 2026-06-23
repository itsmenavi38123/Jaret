from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class FinancialOverviewKPIPreferences(BaseModel):
    user_id: str

    hidden_metric_ids: List[str] = Field(
        default_factory=list,
    )

    pinned_metric_ids: List[str] = Field(
        default_factory=list,
    )

    tile_order: List[str] = Field(
        default_factory=list,
    )

    created_at: datetime
    updated_at: datetime