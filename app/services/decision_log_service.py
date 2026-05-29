from datetime import datetime
from typing import Optional, Dict, Any, List

from app.db import get_collection
from app.models.decision_log import DecisionLog


class DecisionLogService:

    async def create_decision_log(
        self,
        user_id: str,
        action_title: str,
        signal_id: Optional[str] = None,
        signal_surface: Optional[str] = None,
        action_description: Optional[str] = None,
        alternatives_considered: Optional[List[str]] = None,
        consultation_sources: Optional[List[str]] = None,
        owner_state: Optional[str] = None,
        outcome_summary: Optional[str] = None,
        outcome_metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionLog:

        log = DecisionLog(
            user_id=user_id,
            signal_id=signal_id,
            signal_surface=signal_surface,
            action_title=action_title,
            action_description=action_description,
            alternatives_considered=alternatives_considered or [],
            consultation_sources=consultation_sources or [],
            owner_state=owner_state,
            outcome_summary=outcome_summary,
            outcome_metrics=outcome_metrics or {},
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        collection = get_collection("decision_logs")

        await collection.insert_one(
            log.model_dump()
        )

        return log

    async def list_user_decisions(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[DecisionLog]:

        collection = get_collection("decision_logs")

        docs = await collection.find(
            {"user_id": user_id}
        ).sort(
            "created_at",
            -1,
        ).limit(
            limit,
        ).to_list(
            length=limit,
        )

        return [
            DecisionLog(**doc)
            for doc in docs
        ]

    async def attach_outcome(
        self,
        decision_id: str,
        outcome_summary: str,
        outcome_metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[DecisionLog]:

        collection = get_collection("decision_logs")

        existing = await collection.find_one(
            {"_id": decision_id}
        )

        if not existing:
            return None

        await collection.update_one(
            {"_id": decision_id},
            {
                "$set": {
                    "outcome_summary": outcome_summary,
                    "outcome_metrics": outcome_metrics or {},
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        updated = await collection.find_one(
            {"_id": decision_id}
        )

        return DecisionLog(**updated) if updated else None


decision_log_service = DecisionLogService()