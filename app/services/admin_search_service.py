from typing import List

from app.db import get_collection


class AdminSearchService:

    def __init__(self):
        self.collection = get_collection(
            "customer_memory"
        )

    def _serialize_memory(
        self,
        memory: dict
    ):

        if memory.get("_id"):
            memory["_id"] = str(
                memory["_id"]
            )

        return memory

    async def search_memories(
        self,
        query: str,
        user_id: str | None = None,
        observation_type: str | None = None,
        limit: int = 100
    ) -> List[dict]:

        filters = {}

        if user_id:
            filters["user_id"] = user_id

        if observation_type:
            filters["observation_type"] = observation_type

        if query:
            filters["content"] = {
                "$regex": query,
                "$options": "i"
            }

        cursor = (
            self.collection
            .find(filters)
            .sort(
                "created_at",
                -1
            )
            .limit(limit)
        )

        memories = [
            memory async for memory in cursor
        ]

        return [
            self._serialize_memory(memory)
            for memory in memories
        ]

    async def search_by_tag(
        self,
        tag: str,
        limit: int = 100
    ):

        cursor = (
            self.collection
            .find(
                {
                    "tags": tag
                }
            )
            .sort(
                "created_at",
                -1
            )
            .limit(limit)
        )

        memories = [
            memory async for memory in cursor
        ]

        return [
            self._serialize_memory(memory)
            for memory in memories
        ]

    async def search_under_review(
        self,
        limit: int = 100
    ):

        cursor = (
            self.collection
            .find(
                {
                    "under_review": True
                }
            )
            .sort(
                "created_at",
                -1
            )
            .limit(limit)
        )

        memories = [
            memory async for memory in cursor
        ]

        return [
            self._serialize_memory(memory)
            for memory in memories
        ]

    async def search_pinned(
        self,
        limit: int = 100
    ):

        cursor = (
            self.collection
            .find(
                {
                    "pinned": True,
                    "outdated": False
                }
            )
            .sort(
                "created_at",
                -1
            )
            .limit(limit)
        )

        memories = [
            memory async for memory in cursor
        ]

        return [
            self._serialize_memory(memory)
            for memory in memories
        ]