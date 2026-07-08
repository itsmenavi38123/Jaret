from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid

class DreamingRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    pass_number: int
    segment_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    contributors_count: int
    insights_generated_count: int
    summary_text: str
    full_log: str
    status: str = "success"

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
