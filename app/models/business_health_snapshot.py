from datetime import datetime
from typing import Dict, Any, Optional

from beanie import Document
from pydantic import Field


class BusinessHealthSnapshot(Document):

    user_id: str

    overall_score: Optional[int] = None

    overall_label: Optional[str] = None

    classifier_output: Dict[str, Any] = Field(default_factory=dict)

    snapshot_payload: Dict[str, Any] = Field(default_factory=dict)

    ai_summary: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "business_health_snapshots"