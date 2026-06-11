from datetime import datetime

from app.services.customer_memory_service import CustomerMemoryService


class MemoryReviewService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    def _serialize_memory(
        self,
        memory: dict
    ):

        memory = dict(memory)

        if memory.get("_id"):
            memory["_id"] = str(
                memory["_id"]
            )

        return memory

    async def get_review_queue(
        self,
        limit: int = 100
    ):

        memories = await self.memory_service.get_memories_under_review(
            limit=limit
        )

        return [
            self._serialize_memory(memory)
            for memory in memories
        ]

    async def mark_for_review(
        self,
        memory_id: str
    ):

        await self.memory_service.set_under_review(
            memory_id=memory_id,
            under_review=True
        )

    async def approve_memory(
        self,
        memory_id: str
    ):

        await self.memory_service.set_under_review(
            memory_id=memory_id,
            under_review=False
        )

    async def reject_memory(
        self,
        memory_id: str
    ):

        await self.memory_service.mark_outdated(
            memory_id=memory_id
        )

        await self.memory_service.set_under_review(
            memory_id=memory_id,
            under_review=False
        )

    async def update_authority(
        self,
        memory_id: str,
        authority: str
    ):

        await self.memory_service.collection.update_one(
            {
                "_id": memory_id
            },
            {
                "$set": {
                    "authority": authority,
                    "updated_at": datetime.utcnow()
                }
            }
        )

    async def get_memory(
        self,
        memory_id: str
    ):

        memory = await self.memory_service.get_memory_by_id(
            memory_id
        )

        if not memory:
            return None

        return self._serialize_memory(
            memory
        )