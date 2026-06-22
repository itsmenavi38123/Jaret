from datetime import datetime, timezone

from app.db import get_collection
from app.models.financial_overview_kpi_preferences import (
    FinancialOverviewKPIPreferences,
)


class FinancialOverviewKPIPreferencesService:

    def __init__(self):
        self.collection = get_collection(
            "financial_overview_kpi_preferences"
        )

    async def get_preferences(
        self,
        user_id: str,
    ) -> FinancialOverviewKPIPreferences:

        document = await self.collection.find_one(
            {
                "user_id": user_id,
            }
        )

        if not document:

            now = datetime.now(timezone.utc)

            return FinancialOverviewKPIPreferences(
                user_id=user_id,
                hidden_metric_ids=[],
                pinned_metric_ids=[],
                tile_order=[],
                created_at=now,
                updated_at=now,
            )

        return FinancialOverviewKPIPreferences(
            **document,
        )
    
    async def save_preferences(
        self,
        user_id: str,
        hidden_metric_ids: list[str],
        pinned_metric_ids: list[str],
        tile_order: list[str],
    ):

        now = datetime.now(
            timezone.utc,
        )

        await self.collection.update_one(
            {
                "user_id": user_id,
            },
            {
                "$set": {
                    "hidden_metric_ids": hidden_metric_ids,
                    "pinned_metric_ids": pinned_metric_ids,
                    "tile_order": tile_order,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                    "user_id": user_id,
                },
            },
            upsert=True,
        )

        return await self.get_preferences(
            user_id=user_id,
        )


financial_overview_kpi_preferences_service = (
    FinancialOverviewKPIPreferencesService()
)