from pydantic import BaseModel
from datetime import datetime

class FeatureUsage(BaseModel):
    user_id: str
    feature_name: str
    created_at: datetime