from typing import List

from app.services.business_health_snapshot_service import (
    business_health_snapshot_service,
)


class SignalStateService:

    async def get_resolved_signals(
        self,
        user_id: str,
        current_signal_ids: List[str],
    ) -> List[str]:

        snapshots = await business_health_snapshot_service.list_snapshots(
            user_id=user_id,
            limit=2,
        )

        if len(snapshots) < 2:
            return []

        previous = snapshots[1]

        previous_alerts = (
            previous.snapshot_payload.get(
                "active_health_alerts",
                [],
            )
        )

        previous_ids = {
            item.get("signal_id")
            for item in previous_alerts
            if isinstance(item, dict)
        }

        current_ids = set(
            current_signal_ids,
        )

        return list(
            previous_ids - current_ids,
        )


signal_state_service = SignalStateService()