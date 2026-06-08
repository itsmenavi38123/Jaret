from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


class CustomerMemory(BaseModel):

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        alias="_id"
    )

    user_id: str
    path: str
    observation_type: str
    content: str
    agent_name: Optional[str] = None
    session_id: Optional[str] = None
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
    seed: bool = False
    backfilled: bool = False
    under_review: bool = False
    consolidated_from: List[str] = Field(
        default_factory=list
    )
    superseded_by: Optional[str] = None
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