from datetime import datetime
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel
from app.db import get_collection
from app.config import _now_utc

class AdminLog(BaseModel):
    id: str
    admin_user_id: str
    admin_email: str
    target_user_id: str
    target_user_email: str
    action: str  # pause, unpause, resend_verification, force_logout
    timestamp: datetime
    details: Optional[str] = None

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class AdminLogCreate(BaseModel):
    admin_user_id: str
    admin_email: str
    target_user_id: Optional[str] = None
    target_user_email: Optional[str] = None
    action: str
    details: Optional[str] = None

class AdminLogsService:
    def __init__(self):
        self.collection = get_collection("admin_logs")

    async def log_action(self, log_data: AdminLogCreate) -> str:
        """Log an admin action"""
        log_id = str(uuid4())
        log_doc = {
            "_id": log_id,
            "admin_user_id": log_data.admin_user_id,
            "admin_email": log_data.admin_email,
            "target_user_id": log_data.target_user_id,
            "target_user_email": log_data.target_user_email,
            "action": log_data.action,
            "timestamp": _now_utc(),
            "details": log_data.details
        }

        await self.collection.insert_one(log_doc)
        return log_id

    async def get_logs(self, limit: int = 100, skip: int = 0, search: Optional[str] = None, action_type: Optional[str] = None) -> dict:
        """Get admin logs with pagination, search, and action type filtering"""
        query = {}
        
        # 1. Action type filter mapping
        if action_type:
            action_type_lower = action_type.lower()
            if "memory" in action_type_lower:
                # Matches memory-related operations (approve, reject, pin, edit, delete, inspect)
                query["action"] = {"$regex": "memory", "$options": "i"}
            elif "delete" in action_type_lower:
                # Matches delete actions
                query["action"] = {"$regex": "delete", "$options": "i"}
            elif "beta" in action_type_lower:
                # Matches beta account creation or actions
                query["action"] = {"$regex": "beta", "$options": "i"}
            elif "teaser" in action_type_lower:
                # Matches teasers
                query["action"] = {"$regex": "teaser", "$options": "i"}
            elif "rerun" in action_type_lower or "re-run" in action_type_lower:
                # Matches agent reruns
                query["action"] = {"$regex": "rerun|re-run", "$options": "i"}
            elif "broadcast" in action_type_lower:
                # Matches broadcasts
                query["action"] = {"$regex": "broadcast", "$options": "i"}
                
        # 2. Free-text search
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {"action": search_regex},
                {"details": search_regex},
                {"target_user_email": search_regex},
                {"admin_email": search_regex}
            ]
            
        total_count = await self.collection.count_documents(query)
        cursor = self.collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = await cursor.to_list(length=None)
        return {"logs": logs, "total_count": total_count}

    async def get_logs_by_admin(self, admin_user_id: str, limit: int = 50) -> list:
        """Get logs for a specific admin"""
        cursor = self.collection.find({"admin_user_id": admin_user_id}).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(length=None)
        return logs

    async def get_logs_by_target(self, target_user_id: str, limit: int = 50) -> list:
        """Get logs for a specific target user"""
        cursor = self.collection.find({"target_user_id": target_user_id}).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(length=None)
        return logs

# Global instance
admin_logs_service = AdminLogsService()