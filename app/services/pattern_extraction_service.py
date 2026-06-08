from collections import Counter

from app.services.customer_memory_service import CustomerMemoryService
from app.utils.memory_factory import MemoryFactory


class PatternExtractionService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def extract_patterns(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=500
        )

        opportunity_counter = Counter()

        for memory in memories:

            if memory.get(
                "observation_type"
            ) != "outcome":
                continue

            supporting_data = memory.get(
                "supporting_data",
                {}
            )

            opportunity_name = supporting_data.get(
                "opportunity_name"
            )

            if opportunity_name:
                opportunity_counter[
                    opportunity_name
                ] += 1

        created_patterns = 0

        for name, count in opportunity_counter.items():

            if count < 2:
                continue

            already_exists = False

            for memory in memories:

                if (
                    memory.get(
                        "observation_type"
                    ) == "pattern"
                    and memory.get(
                        "supporting_data",
                        {}
                    ).get(
                        "opportunity_name"
                    ) == name
                ):
                    already_exists = True
                    break

            if already_exists:
                continue

            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="pattern",
                content=f"Repeated interest detected in '{name}' opportunities.",
                agent_name="dreaming_system",
                session_id="pattern_extraction",
                confidence="high",
                tags=[
                    "pattern",
                    "opportunity_interest"
                ],
                supporting_data={
                    "opportunity_name": name,
                    "occurrence_count": count
                }
            )

            memory.authority = "dreaming_pass"

            await self.memory_service.create_memory(
                memory
            )

            created_patterns += 1

        return created_patterns