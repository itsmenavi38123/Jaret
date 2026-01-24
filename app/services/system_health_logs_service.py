from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import uuid4
from app.db import get_collection
from app.models.system_health_logs import SystemHealthLog, SystemHealthLogCreate
from app.config import _now_utc

class SystemHealthLogsService:
    def __init__(self):
        self.collection = get_collection("system_health_logs")

    async def log_error(self, log_data: SystemHealthLogCreate) -> str:
        """Log a system health error"""
        log_id = str(uuid4())
        log_doc = {
            "_id": log_id,
            "log_type": log_data.log_type,
            "service": log_data.service,
            "endpoint": log_data.endpoint,
            "error_message": log_data.error_message,
            "status_code": log_data.status_code,
            "user_id": log_data.user_id,
            "request_id": log_data.request_id,
            "metadata": log_data.metadata,
            "timestamp": _now_utc()
        }

        await self.collection.insert_one(log_doc)
        return log_id

    async def get_error_counts(self, hours: int = 24) -> Dict[str, int]:
        """Get error counts by type for the last N hours"""
        since = _now_utc() - timedelta(hours=hours)

        pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {"$group": {"_id": "$log_type", "count": {"$sum": 1}}}
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)

        counts = {}
        for result in results:
            counts[result["_id"]] = result["count"]

        return counts

    async def get_recent_errors(self, limit: int = 50) -> List[SystemHealthLog]:
        """Get recent error logs"""
        cursor = self.collection.find().sort("timestamp", -1).limit(limit)
        docs = await cursor.to_list(length=None)

        return [SystemHealthLog(**doc) for doc in docs]

    async def get_service_errors(self, service: str, hours: int = 24) -> List[SystemHealthLog]:
        """Get errors for a specific service in the last N hours"""
        since = _now_utc() - timedelta(hours=hours)

        cursor = self.collection.find({
            "service": service,
            "timestamp": {"$gte": since}
        }).sort("timestamp", -1)

        docs = await cursor.to_list(length=None)
        return [SystemHealthLog(**doc) for doc in docs]

# Global instance
system_health_logs_service = SystemHealthLogsService()