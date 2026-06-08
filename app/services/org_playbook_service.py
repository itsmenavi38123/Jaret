from typing import List, Optional

from app.db import get_collection
from app.models.org_playbook import OrgPlaybook


class OrgPlaybookService:

    def __init__(self):
        self.collection = get_collection("org_playbook")

    async def create_entry(
        self,
        entry: OrgPlaybook
    ) -> str:

        data = entry.model_dump(
            by_alias=True
        )

        result = await self.collection.insert_one(
            data
        )

        return str(result.inserted_id)

    async def get_entries(
        self,
        limit: int = 100
    ) -> List[dict]:

        cursor = (
            self.collection
            .find({})
            .sort(
                "created_at",
                -1
            )
            .limit(limit)
        )

        return [
            doc async for doc in cursor
        ]

    async def get_by_path(
        self,
        path: str
    ) -> Optional[dict]:

        return await self.collection.find_one(
            {
                "path": path
            }
        )