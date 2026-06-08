from typing import List, Optional

from app.db import get_collection


class MemorySearchService:

    def __init__(self):
        self.collection = get_collection("customer_memory")

    async def search_by_tag(
        self,
        user_id: str,
        tag: str,
        limit: int = 100
    ) -> List[dict]:

        cursor = (
            self.collection
            .find(
                {
                    "user_id": user_id,
                    "tags": tag
                }
            )
            .limit(limit)
        )

        return [doc async for doc in cursor]

    async def search_by_observation_type(
        self,
        user_id: str,
        observation_type: str,
        limit: int = 100
    ) -> List[dict]:

        cursor = (
            self.collection
            .find(
                {
                    "user_id": user_id,
                    "observation_type": observation_type
                }
            )
            .limit(limit)
        )

        return [doc async for doc in cursor]

    async def search_by_agent(
        self,
        user_id: str,
        agent_name: str,
        limit: int = 100
    ) -> List[dict]:

        cursor = (
            self.collection
            .find(
                {
                    "user_id": user_id,
                    "agent_name": agent_name
                }
            )
            .limit(limit)
        )

        return [doc async for doc in cursor]

    async def search_by_path(
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
            .limit(limit)
        )

        return [doc async for doc in cursor]