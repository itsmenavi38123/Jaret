from datetime import datetime

from app.db import get_collection


class CustomerSummaryService:

    def __init__(self):
        self.collection = get_collection("customer_memory")

    async def get_summary(
        self,
        user_id: str
    ):

        path = f"/memories/customer_{user_id}/_summary.md"

        return await self.collection.find_one(
            {
                "user_id": user_id,
                "path": path
            }
        )

    async def create_summary(
        self,
        user_id: str,
        content: str
    ):

        path = f"/memories/customer_{user_id}/_summary.md"

        existing = await self.get_summary(
            user_id
        )

        if existing:
            return existing

        document = {
            "user_id": user_id,
            "path": path,
            "observation_type": "living_summary",
            "content": content,
            "agent_name": "dreaming_system",
            "confidence": "high",
            "tags": ["summary"],
            "pinned": True,
            "outdated": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        await self.collection.insert_one(
            document
        )

        return document

    async def update_summary(
        self,
        user_id: str,
        content: str
    ):

        path = f"/memories/customer_{user_id}/_summary.md"

        await self.collection.update_one(
            {
                "user_id": user_id,
                "path": path
            },
            {
                "$set": {
                    "content": content,
                    "updated_at": datetime.utcnow()
                }
            }
        )