from typing import Dict, Any, List, Optional

from app.models.business_health_snapshot import (
    BusinessHealthSnapshot,
)


class BusinessHealthSnapshotService:

    async def create_snapshot(
        self,
        user_id: str,
        business_health_payload: Dict[str, Any],
        classifier_output: Optional[Dict[str, Any]] = None,
        ai_summary: Optional[str] = None,
    ) -> BusinessHealthSnapshot:

        overall = business_health_payload.get(
            "overall",
            {},
        )

        snapshot = BusinessHealthSnapshot(
            user_id=user_id,
            overall_score=overall.get("score"),
            overall_label=overall.get("label"),
            classifier_output=classifier_output or {},
            snapshot_payload=business_health_payload,
            ai_summary=ai_summary,
        )

        await snapshot.insert()

        return snapshot

    async def list_snapshots(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[BusinessHealthSnapshot]:

        return await (
            BusinessHealthSnapshot.find(
                BusinessHealthSnapshot.user_id == user_id,
            )
            .sort(-BusinessHealthSnapshot.created_at)
            .limit(limit)
            .to_list()
        )

    async def compare_snapshots(
        self,
        current_snapshot_id: str,
        previous_snapshot_id: str,
    ) -> Dict[str, Any]:

        current = await BusinessHealthSnapshot.get(
            current_snapshot_id,
        )

        previous = await BusinessHealthSnapshot.get(
            previous_snapshot_id,
        )

        if not current or not previous:

            return {
                "comparison": None,
            }

        current_score = current.overall_score or 0
        previous_score = previous.overall_score or 0

        score_delta = current_score - previous_score

        current_alerts = (
            current.snapshot_payload.get(
                "active_health_alerts",
                [],
            )
        )

        previous_alerts = (
            previous.snapshot_payload.get(
                "active_health_alerts",
                [],
            )
        )

        current_signal_ids = {
            item.get("signal_id")
            for item in current_alerts
        }

        previous_signal_ids = {
            item.get("signal_id")
            for item in previous_alerts
        }

        return {
            "score_delta": score_delta,
            "new_alerts": list(
                current_signal_ids - previous_signal_ids
            ),
            "resolved_alerts": list(
                previous_signal_ids - current_signal_ids
            ),
            "current_snapshot_created_at": current.created_at,
            "previous_snapshot_created_at": previous.created_at,
        }


business_health_snapshot_service = (BusinessHealthSnapshotService())