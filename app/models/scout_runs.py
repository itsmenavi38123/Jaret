from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class ScoutRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    business_id: str
    run_type: str
    user_query: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"
    cards_returned: int = 0
    dedup_skipped: int = 0
    tracked_skipped: int = 0
    small_market_flag: bool = False
    types_searched: List[str] = Field(default_factory=list)
    queries_run: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }