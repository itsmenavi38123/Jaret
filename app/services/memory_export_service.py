from app.services.customer_memory_service import CustomerMemoryService
from app.services.customer_summary_service import CustomerSummaryService


class MemoryExportService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()
        self.summary_service = CustomerSummaryService()

    def _serialize_memory(
        self,
        memory: dict
    ):

        if not memory:
            return memory

        memory = dict(memory)

        if memory.get("_id"):
            memory["_id"] = str(
                memory["_id"]
            )

        return memory

    async def export_customer_memories(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=10000
        )

        return [
            self._serialize_memory(memory)
            for memory in memories
        ]

    async def export_patterns(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=10000
        )

        return [
            self._serialize_memory(memory)
            for memory in memories
            if memory.get("observation_type") == "pattern"
        ]

    async def export_learnings(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=10000
        )

        return [
            self._serialize_memory(memory)
            for memory in memories
            if memory.get("observation_type") == "learning"
        ]

    async def export_behavior_patterns(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=10000
        )

        return [
            self._serialize_memory(memory)
            for memory in memories
            if memory.get("observation_type") == "behavior_pattern"
        ]

    async def export_summary(
        self,
        user_id: str
    ):

        summary = await self.summary_service.get_summary(
            user_id
        )

        return self._serialize_memory(
            summary
        )