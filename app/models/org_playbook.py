from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


class OrgPlaybook(BaseModel):

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        alias="_id"
    )

    path: str

    source_type: str

    observation_type: str

    content: str

    supporting_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )

    confidence: str = "medium"

    tags: List[str] = Field(
        default_factory=list
    )

    pinned: bool = False

    outdated: bool = False

    date_marked_outdated: Optional[datetime] = None

    authority: Optional[str] = None

    under_review: bool = False

    consolidated_from: List[str] = Field(
        default_factory=list
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }