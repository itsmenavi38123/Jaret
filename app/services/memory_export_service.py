from io import StringIO
import csv

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

    async def export_customer_memories_csv(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=10000
        )

        output = StringIO()

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "memory_id",
                "user_id",
                "path",
                "observation_type",
                "content",
                "agent_name",
                "session_id",
                "confidence",
                "pinned",
                "outdated",
                "authority",
                "seed",
                "backfilled",
                "under_review",
                "created_at",
                "updated_at"
            ]
        )

        writer.writeheader()

        for memory in memories:

            writer.writerow({
                "memory_id": str(memory.get("_id")),
                "user_id": memory.get("user_id"),
                "path": memory.get("path"),
                "observation_type": memory.get("observation_type"),
                "content": memory.get("content"),
                "agent_name": memory.get("agent_name"),
                "session_id": memory.get("session_id"),
                "confidence": memory.get("confidence"),
                "pinned": memory.get("pinned"),
                "outdated": memory.get("outdated"),
                "authority": memory.get("authority"),
                "seed": memory.get("seed"),
                "backfilled": memory.get("backfilled"),
                "under_review": memory.get("under_review"),
                "created_at": memory.get("created_at"),
                "updated_at": memory.get("updated_at")
            })

        return output.getvalue()

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