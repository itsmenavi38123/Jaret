from datetime import datetime

from app.models.customer_memory import CustomerMemory
from app.utils.memory_paths import MemoryPaths


class MemoryFactory:

    @staticmethod
    def create_memory(
        user_id: str,
        observation_type: str,
        content: str,
        agent_name: str | None = None,
        session_id: str | None = None,
        supporting_data: dict | None = None,
        confidence: str = "medium",
        tags: list[str] | None = None,
        path: str | None = None,
        authority: str | None = None,
        seed: bool = False,
        backfilled: bool = False,
        under_review: bool = False,
    ) -> CustomerMemory:

        now = datetime.utcnow()

        memory_path = path or MemoryPaths.customer_memory_file(
            user_id=user_id,
            agent_name=agent_name or "system",
            session_id=session_id or "system",
            dt=now,
        )

        return CustomerMemory(
            user_id=user_id,
            path=memory_path,
            observation_type=observation_type,
            content=content,
            agent_name=agent_name,
            session_id=session_id,
            supporting_data=supporting_data or {},
            confidence=confidence,
            tags=tags or [],
            authority=authority,
            seed=seed,
            backfilled=backfilled,
            under_review=under_review,
        )