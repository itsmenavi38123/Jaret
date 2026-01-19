from app.db import get_collection
from app.models.feature_usage import FeatureUsage
from datetime import datetime

class FeatureUsageService:
    def __init__(self):
        self.collection = get_collection("feature_usage")

    async def log_usage(self, user_id: str, feature_name: str):
        await self.collection.insert_one({
            "user_id": user_id,
            "feature_name": feature_name,
            "created_at": datetime.utcnow()
        })

    async def get_unique_users_per_feature(self, feature_name: str, beta_user_ids: list):
        pipeline = [
            {"$match": {"feature_name": feature_name, "user_id": {"$in": beta_user_ids}}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "count"}
        ]
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        return result[0]["count"] if result else 0

feature_usage_service = FeatureUsageService()