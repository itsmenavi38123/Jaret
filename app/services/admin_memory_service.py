from datetime import datetime

from app.db import get_collection
from app.services.customer_memory_service import CustomerMemoryService


class AdminMemoryService:

    def __init__(self):
        self.collection = get_collection(
            "customer_memory"
        )
        self.memory_service = CustomerMemoryService()

    def _serialize_memory(
        self,
        memory: dict
    ):

        if memory.get("_id"):
            memory["_id"] = str(
                memory["_id"]
            )

        return memory

    async def get_customer_memories(
        self,
        user_id: str,
        include_outdated: bool = False,
        page: int = 1,
        page_size: int = 10,
        observation_type: str | None = None,
        agent_name: str | None = None,
        tags: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ):

        query = {
            "user_id": user_id
        }

        if not include_outdated:
            query["outdated"] = False

        if observation_type:
            query["observation_type"] = observation_type

        if agent_name:
            query["agent_name"] = agent_name

        if tags:
            query["tags"] = {
                "$in": tags
            }

        if start_date or end_date:

            query["created_at"] = {}

            if start_date:
                query["created_at"]["$gte"] = start_date

            if end_date:
                query["created_at"]["$lte"] = end_date

        skip = (page - 1) * page_size

        total_count = await self.collection.count_documents(
            query
        )

        cursor = (
            self.collection
            .find(query)
            .sort([
                ("pinned", -1),
                ("outdated", 1),
                ("created_at", -1)
            ])
            .skip(skip)
            .limit(page_size)
        )

        memories = [
            doc async for doc in cursor
        ]

        return {
            "memories": [
                self._serialize_memory(memory)
                for memory in memories
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (
                    total_count + page_size - 1
                ) // page_size,
                "has_next": (
                    page * page_size
                ) < total_count,
                "has_prev": page > 1
            }
        }

    async def edit_memory(
        self,
        memory_id: str,
        updated_content: str
    ):

        memory = await self.memory_service.get_memory_by_id(
            memory_id
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        await self.memory_service.mark_outdated(
            memory_id
        )

        new_memory = dict(memory)

        new_memory.pop("_id", None)

        new_memory["content"] = updated_content
        new_memory["outdated"] = False
        new_memory["superseded_by"] = None
        new_memory["updated_at"] = datetime.utcnow()

        result = await self.collection.insert_one(
            new_memory
        )

        await self.memory_service.set_superseded_by(
            memory_id=memory_id,
            superseded_by=str(result.inserted_id)
        )

        return str(result.inserted_id)

    async def soft_delete_memory(
        self,
        memory_id: str
    ):

        await self.memory_service.mark_outdated(
            memory_id
        )

    async def hard_delete_memory(
        self,
        memory_id: str
    ):

        await self.collection.delete_one(
            {
                "_id": memory_id
            }
        )

    async def export_customer_memories(
        self,
        user_id: str
    ):

        cursor = (
            self.collection
            .find(
                {
                    "user_id": user_id
                }
            )
            .sort(
                "created_at",
                -1
            )
        )

        memories = [
            doc async for doc in cursor
        ]

        return [
            self._serialize_memory(memory)
            for memory in memories
        ]