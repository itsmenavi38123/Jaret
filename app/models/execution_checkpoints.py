from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class ExecutionCheckpoint(BaseModel):

    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    opportunity_id: str
    scheduled_at: datetime
    label: str  
    status: str = "pending"
    auto_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    owner_responses: Optional[Dict[str, Any]] = Field(default_factory=dict)
    computed_status: Optional[str] = None
    alert_modal: bool = False
    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }