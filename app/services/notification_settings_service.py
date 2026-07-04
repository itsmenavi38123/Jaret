from datetime import datetime, timezone

from app.db import get_collection
from app.models.notification_settings import (
    NotificationSettings,
    NotificationSettingsRequest,
)


class NotificationSettingsService:

    def __init__(self):
        self.collection = get_collection("notification_settings")

    async def get_settings(self, user_id: str) -> NotificationSettings:
        document = await self.collection.find_one({"user_id": user_id})

        if not document:
            now = datetime.now(timezone.utc)
            return NotificationSettings(
                user_id=user_id,
                created_at=now,
                updated_at=now,
            )

        return NotificationSettings(**document)

    async def save_settings(
        self,
        user_id: str,
        settings: NotificationSettingsRequest,
    ) -> NotificationSettings:
        now = datetime.now(timezone.utc)

        await self.collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    **settings.dict(),
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                    "user_id": user_id,
                },
            },
            upsert=True,
        )

        return await self.get_settings(user_id=user_id)


notification_settings_service = NotificationSettingsService()
