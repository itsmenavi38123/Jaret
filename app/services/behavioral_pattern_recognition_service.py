from app.services.customer_memory_service import CustomerMemoryService
from app.utils.memory_factory import MemoryFactory


class BehavioralPatternRecognitionService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def extract_behavior_patterns(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=500
        )

        decision_count = 0
        outcome_count = 0
        learning_count = 0

        for memory in memories:

            observation_type = memory.get(
                "observation_type"
            )

            if observation_type == "decision":
                decision_count += 1

            elif observation_type == "outcome":
                outcome_count += 1

            elif observation_type == "learning":
                learning_count += 1

        behavior_patterns = []

        if decision_count >= 3:
            behavior_patterns.append(
                "Owner demonstrates recurring engagement with strategic planning activities."
            )

        if outcome_count >= 5:
            behavior_patterns.append(
                "Business has accumulated sufficient historical outcomes for future recommendation calibration."
            )

        if learning_count >= 3:
            behavior_patterns.append(
                "Owner behavior patterns are becoming increasingly predictable through historical interactions."
            )

        created = 0

        for pattern in behavior_patterns:

            path = (
                f"/memories/customer_{user_id}/behavior/"
                f"{self._slugify(pattern)}"
            )

            existing = await self.memory_service.get_by_path(
                path=path
            )

            if existing:
                continue

            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="behavior_pattern",
                content=pattern,
                authority="dreaming_pass",
                confidence="medium",
                tags=["behavior_pattern"],
                path=path
            )

            await self.memory_service.create_memory(
                memory
            )

            created += 1

        return created

    def _slugify(
        self,
        text: str
    ):

        return (
            text.lower()
            .replace(" ", "_")
            .replace(".", "")
            .replace(",", "")
        )