from datetime import datetime

from app.db import get_collection


class AdminNotificationService:

    def __init__(self):
        self.collection = get_collection(
            "admin_notifications"
        )

    async def create_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "memory"
    ):

        document = {
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "resolved": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        await self.collection.insert_one(
            document
        )

        return document

    async def get_open_notifications(self):

        cursor = self.collection.find(
            {
                "resolved": False
            }
        ).sort(
            "created_at",
            -1
        )

        return [
            doc async for doc in cursor
        ]

    async def resolve_notification(
        self,
        notification_id: str
    ):

        await self.collection.update_one(
            {
                "_id": notification_id
            },
            {
                "$set": {
                    "resolved": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )