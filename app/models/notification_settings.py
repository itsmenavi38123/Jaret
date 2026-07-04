from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class CustomThreshold(BaseModel):
    id: str
    label: str


class NotificationSettings(BaseModel):
    user_id: str

    push_enabled: bool = True
    in_app_enabled: bool = True
    email_enabled: bool = True
    escalate_after: str = "2_days"

    critical_health_alerts: bool = True
    watch_items: bool = True
    action_reminders: bool = False
    opportunities: bool = True
    connection_problems: bool = True
    weekly_report: bool = True
    monthly_summary: bool = True

    quiet_hours_start: str = "21:00"
    quiet_hours_end: str = "07:00"

    report_recipient_emails: List[str] = Field(default_factory=list)
    custom_thresholds: List[CustomThreshold] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime


class NotificationSettingsRequest(BaseModel):
    push_enabled: bool = True
    in_app_enabled: bool = True
    email_enabled: bool = True
    escalate_after: str = "2_days"

    critical_health_alerts: bool = True
    watch_items: bool = True
    action_reminders: bool = False
    opportunities: bool = True
    connection_problems: bool = True
    weekly_report: bool = True
    monthly_summary: bool = True

    quiet_hours_start: str = "21:00"
    quiet_hours_end: str = "07:00"

    report_recipient_emails: List[str] = Field(default_factory=list)
    custom_thresholds: List[CustomThreshold] = Field(default_factory=list)
