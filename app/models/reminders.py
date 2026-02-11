"""Reminder models for dashboard notifications."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Reminder(BaseModel):
    """Reminder object returned in API responses."""
    id: Optional[str] = None
    label: str = Field(..., description="Human-readable reminder text")
    due_date: datetime = Field(..., description="When the reminder is due")
    action_type: Literal[
        "invoice_followup",
        "bill_payment",
        "payroll_approval",
        "tax_payment",
        "general"
    ] = Field(default="general", description="Type of reminder")
    category: Literal["cash", "operations", "compliance", "general"] = Field(
        default="general", description="Category for grouping"
    )
    priority: Literal["critical", "high", "normal", "low"] = Field(
        default="normal", description="Priority level"
    )
    days_until_due: Optional[int] = Field(
        default=None, description="Days until due (negative if overdue)"
    )
    related_entity: Optional[str] = Field(
        default=None, description="Related invoice/bill/vendor ID or name"
    )

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class TaxCalendarEvent(BaseModel):
    """Tax calendar event for compliance reminders."""
    id: Optional[str] = None
    description: str
    due_date: datetime
    frequency: Literal["weekly", "monthly", "quarterly", "annual"]
    
    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
