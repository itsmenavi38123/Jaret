from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ConnectorSyncJob(BaseModel):
    id: str = Field(alias="_id")  # Format: "{user_id}_{connector_type}"
    user_id: str
    connector_type: str  # "quickbooks", "xero", "square", "shopify"
    last_sync_status: str  # "success" or "failed"
    last_sync_time: datetime
    sync_retry_count: int = 0
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
