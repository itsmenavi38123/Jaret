from datetime import datetime
from pydantic import BaseModel, Field


class ScoutRateLimit(BaseModel):
    business_id: str
    date: str
    on_demand_count: int = 0
    last_search_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    class Config:
        populate_by_name = True
        from_attributes = True
