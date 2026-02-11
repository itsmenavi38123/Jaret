"""Tax calendar model for compliance reminders."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TaxCalendar(BaseModel):
    """Tax calendar entry for compliance tracking."""
    id: Optional[str] = Field(None, alias="_id")
    description: str = Field(..., description="Tax event description")
    due_date: datetime = Field(..., description="When the tax event is due")
    frequency: Literal["weekly", "monthly", "quarterly", "annual"] = Field(
        ..., description="How often this event recurs"
    )
    category: Literal["federal", "state", "local", "payroll"] = Field(
        default="federal", description="Tax category"
    )
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
