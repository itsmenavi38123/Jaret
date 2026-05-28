from datetime import datetime
from typing import Optional, Dict, Any, List

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

        await log.insert()

        return log

    async def list_user_decisions(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[DecisionLog]:

        return await (
            DecisionLog.find(
                DecisionLog.user_id == user_id,
            )
            .sort(-DecisionLog.created_at)
            .limit(limit)
            .to_list()
        )

    async def attach_outcome(
        self,
        decision_id: str,
        outcome_summary: str,
        outcome_metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[DecisionLog]:

        decision = await DecisionLog.get(
            decision_id,
        )

        if not decision:
            return None

        decision.outcome_summary = outcome_summary
        decision.outcome_metrics = outcome_metrics or {}
        decision.updated_at = datetime.utcnow()

        await decision.save()

        return decision


decision_log_service = DecisionLogService()