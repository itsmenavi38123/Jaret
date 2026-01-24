from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.config import _now_utc

class SystemHealthLog(BaseModel):
    id: str
    log_type: str  # 'api_error', 'webhook_failure', 'job_failure', 'rate_limit_warning', 'third_party_error'
    service: Optional[str] = None  # 'quickbooks', 'xero', 'openai', 'weather', etc.
    endpoint: Optional[str] = None
    error_message: str
    status_code: Optional[int] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class SystemHealthLogCreate(BaseModel):
    log_type: str
    service: Optional[str] = None
    endpoint: Optional[str] = None
    error_message: str
    status_code: Optional[int] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None