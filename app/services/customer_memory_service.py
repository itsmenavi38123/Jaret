from datetime import datetime
from typing import List, Optional

from app.db import get_collection
from app.models.customer_memory import CustomerMemory


class CustomerMemoryService:

    def __init__(self):
        self.collection = get_collection("customer_memory")

    async def create_memory(
        self,
        memory: CustomerMemory
    ) -> str:

        data = memory.model_dump(
            by_alias=True
        )

        result = await self.collection.insert_one(
            data
        )

        return str(result.inserted_id)

    async def get_memory_by_user(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[dict]:

        cursor = (
            self.collection
            .find(
                {
                    "user_id": user_id,
                    "outdated": False
                }
            )
            .sort(
                "created_at",
                -1
            )
            .limit(limit)
        )

        return [doc async for doc in cursor]

    async def get_memory_by_id(
        self,
        memory_id: str
    ) -> Optional[dict]:

        return await self.collection.find_one(
            {
                "_id": memory_id
            }
        )

    async def get_memories_by_path_prefix(
        self,
        path_prefix: str,
        limit: int = 100
    ) -> List[dict]:

        cursor = (
            self.collection
            .find(
                {
                    "path": {
                        "$regex": f"^{path_prefix}"
                    }
                }
            )
            .sort(
                "created_at",
                -1
            )
            .limit(limit)
        )

        return [doc async for doc in cursor]

    async def get_pinned_memories(
        self,
        user_id: str
    ) -> List[dict]:

        cursor = (
            self.collection
            .find(
                {
                    "user_id": user_id,
                    "pinned": True,
                    "outdated": False
                }
            )
            .sort(
                "created_at",
                -1
            )
        )

        return [doc async for doc in cursor]

    async def pin_memory(
        self,
        memory_id: str
    ):

        await self.collection.update_one(
            {
                "_id": memory_id
            },
            {
                "$set": {
                    "pinned": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )

    async def unpin_memory(
        self,
        memory_id: str
    ):

        await self.collection.update_one(
            {
                "_id": memory_id
            },
            {
                "$set": {
                    "pinned": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )

    async def mark_outdated(
        self,
        memory_id: str
    ):

        await self.collection.update_one(
            {
                "_id": memory_id
            },
            {
                "$set": {
                    "outdated": True,
                    "date_marked_outdated": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

    async def set_superseded_by(
        self,
        memory_id: str,
        superseded_by: str
    ):

        await self.collection.update_one(
            {
                "_id": memory_id
            },
            {
                "$set": {
                    "superseded_by": superseded_by,
                    "updated_at": datetime.utcnow()
                }
            }
        )

    async def set_under_review(
        self,
        memory_id: str,
        under_review: bool = True
    ):

        await self.collection.update_one(
            {
                "_id": memory_id
            },
            {
                "$set": {
                    "under_review": under_review,
                    "updated_at": datetime.utcnow()
                }
            }
        )

    async def get_by_path(
        self,
        path: str
    ) -> Optional[dict]:

        return await self.collection.find_one(
            {
                "path": path
            }
        )