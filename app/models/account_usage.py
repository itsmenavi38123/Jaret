# backend/app/models/account_usage.py
from datetime import datetime
from pydantic import BaseModel, Field

class AccountUsageDaily(BaseModel):
    account_id: str
    date: str  # YYYY-MM-DD representation of the date
    cost_cents_total: int = 0
    manual_refresh_count: int = 0
    scenario_run_count: int = 0
    dia_upload_count: int = 0
    soft_alert_fired: bool = False
    last_call_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
