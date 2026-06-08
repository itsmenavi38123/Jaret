from app.services.customer_memory_service import CustomerMemoryService
from app.services.customer_summary_service import CustomerSummaryService


class MemorySummaryService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()
        self.summary_service = CustomerSummaryService()

    async def generate_summary(
        self,
        user_id: str
    ) -> str:

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=500
        )

        onboarding_count = 0
        decision_count = 0
        outcome_count = 0
        pattern_count = 0

        for memory in memories:

            observation_type = memory.get(
                "observation_type"
            )

            if observation_type == "onboarding":
                onboarding_count += 1

            elif observation_type == "decision":
                decision_count += 1

            elif observation_type == "outcome":
                outcome_count += 1

            elif observation_type == "pattern":
                pattern_count += 1

        summary = f"""
# Customer Memory Summary

Total Memories: {len(memories)}

Onboarding Memories: {onboarding_count}

Decision Memories: {decision_count}

Outcome Memories: {outcome_count}

Pattern Memories: {pattern_count}
""".strip()

        return summary

    async def refresh_summary(
        self,
        user_id: str
    ):

        summary = await self.generate_summary(
            user_id
        )

        existing = await self.summary_service.get_summary(
            user_id
        )

        if existing:

            await self.summary_service.update_summary(
                user_id=user_id,
                content=summary
            )

        else:

            await self.summary_service.create_summary(
                user_id=user_id,
                content=summary
            )