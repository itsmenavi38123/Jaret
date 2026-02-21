from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.db import get_collection


class ScenarioPlanningService:
    """Service to persist and retrieve scenario planning chat threads."""

    def __init__(self):
        self.collection = get_collection("scenario_chats")

    async def save_chat_thread(
        self, user_id: str, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Insert a new chat thread for the user.

        Stores messages (list of dicts with 'role' and 'content') and metadata.
        Returns inserted id string.
        """
        now = datetime.utcnow()
        doc = {
            "user_id": user_id,
            "messages": messages,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def get_user_threads(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
        return [doc async for doc in cursor]
