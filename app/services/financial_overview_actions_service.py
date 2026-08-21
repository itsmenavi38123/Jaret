# backend/app/services/financial_overview_actions_service.py
"""
Financial Overview Actions Service
Manages insight card action buttons (acknowledge, snooze, resolve) and persists user state.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from app.db import get_collection


class FinancialOverviewActionsService:
    """
    Manages state mutations for Financial Overview insight cards.
    Tracks acknowledged (read) cards, snoozed cards, and resolved signals.
    """

    def __init__(self):
        self.actions_collection_name = "financial_overview_user_actions"
        self.resolved_collection_name = "financial_overview_resolved_signals"

    def _get_actions_collection(self):
        return get_collection(self.actions_collection_name)

    def _get_resolved_collection(self):
        return get_collection(self.resolved_collection_name)

    async def acknowledge_insight(self, user_id: str, insight_id: str) -> Dict[str, Any]:
        """
        Marks an insight card as acknowledged (read). Stops glow state in UI.
        """
        now = datetime.now(timezone.utc)
        actions_col = self._get_actions_collection()

        await actions_col.update_one(
            {"user_id": user_id, "insight_id": insight_id},
            {
                "$set": {
                    "is_read": True,
                    "acknowledged_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

        return {
            "insight_id": insight_id,
            "status": "acknowledged",
            "is_read": True,
            "acknowledged_at": now.isoformat(),
        }

    async def snooze_insight(
        self, user_id: str, insight_id: str, snooze_days: int = 7
    ) -> Dict[str, Any]:
        """
        Snoozes an insight card for N days. Hides it from active surface until expired.
        """
        now = datetime.now(timezone.utc)
        snooze_until = now + timedelta(days=snooze_days)
        actions_col = self._get_actions_collection()

        await actions_col.update_one(
            {"user_id": user_id, "insight_id": insight_id},
            {
                "$set": {
                    "is_snoozed": True,
                    "snoozed_at": now,
                    "snooze_until": snooze_until,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

        return {
            "insight_id": insight_id,
            "status": "snoozed",
            "is_snoozed": True,
            "snooze_until": snooze_until.isoformat(),
        }

    async def resolve_insight(self, user_id: str, insight_id: str) -> Dict[str, Any]:
        """
        Resolves a signal. Triggers green resolved treatment, plays resolve animation,
        starts 24h active-surface timer, and persists permanent record in Memory.
        """
        now = datetime.now(timezone.utc)
        dwell_expires_at = now + timedelta(hours=24)
        resolved_col = self._get_resolved_collection()

        record = {
            "user_id": user_id,
            "insight_id": insight_id,
            "resolved_at": now,
            "dwell_expires_at": dwell_expires_at,
        }

        await resolved_col.update_one(
            {"user_id": user_id, "insight_id": insight_id},
            {"$set": record},
            upsert=True,
        )

        # Also mark acknowledged
        await self.acknowledge_insight(user_id=user_id, insight_id=insight_id)

        return {
            "insight_id": insight_id,
            "status": "resolved",
            "resolved_at": now.isoformat(),
            "dwell_expires_at": dwell_expires_at.isoformat(),
        }

    async def apply_user_actions_to_insights(
        self, user_id: str, insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merges stored user actions (read, snooze, resolved) into the generated insights list.
        """
        now = datetime.now(timezone.utc)
        actions_col = self._get_actions_collection()
        resolved_col = self._get_resolved_collection()

        actions_cursor = actions_col.find({"user_id": user_id})
        actions_list = await actions_cursor.to_list(length=100)
        actions_map = {a["insight_id"]: a for a in actions_list}

        resolved_cursor = resolved_col.find({"user_id": user_id})
        resolved_list = await resolved_cursor.to_list(length=100)
        resolved_map = {r["insight_id"]: r for r in resolved_list}

        processed = []
        for item in insights:
            iid = item.get("id") or item.get("headline")
            action = actions_map.get(iid, {})
            resolution = resolved_map.get(iid, {})

            # Check snooze expiry
            snooze_until = action.get("snooze_until")
            if action.get("is_snoozed") and snooze_until:
                if isinstance(snooze_until, str):
                    snooze_until_dt = datetime.fromisoformat(snooze_until)
                else:
                    snooze_until_dt = snooze_until

                if snooze_until_dt > now:
                    continue  # Skip snoozed items still within window

            # Check resolution
            if resolution:
                item["status_label"] = "RESOLVED"
                item["sev"] = "good"
                item["resolved_at"] = (
                    resolution["resolved_at"].isoformat()
                    if isinstance(resolution["resolved_at"], datetime)
                    else str(resolution["resolved_at"])
                )

            item["is_read"] = action.get("is_read", False)
            item["is_snoozed"] = action.get("is_snoozed", False)
            processed.append(item)

        return processed


financial_overview_actions_service = FinancialOverviewActionsService()
