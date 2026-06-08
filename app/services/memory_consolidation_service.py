from datetime import datetime

from app.services.customer_memory_service import CustomerMemoryService

class MemoryConsolidationService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def consolidate_patterns(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=1000
        )

        pattern_groups = {}

        for memory in memories:

            if memory.get(
                "observation_type"
            ) != "pattern":
                continue

            key = memory.get(
                "content"
            )

            pattern_groups.setdefault(
                key,
                []
            ).append(
                memory
            )

        consolidated_count = 0

        for content, group in pattern_groups.items():

            if len(group) < 2:
                continue

            newest = sorted(
                group,
                key=lambda x: x.get(
                    "created_at"
                ),
                reverse=True
            )[0]

            for memory in group:

                if memory.get("_id") == newest.get("_id"):
                    continue

                await self.memory_service.collection.update_one(
                    {
                        "_id": memory["_id"]
                    },
                    {
                        "$set": {
                            "outdated": True,
                            "date_marked_outdated": datetime.utcnow(),
                            "superseded_by": newest.get(
                                "path"
                            ),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

            await self.memory_service.collection.update_one(
                {
                    "_id": newest["_id"]
                },
                {
                    "$set": {
                        "consolidated_from": [
                            m.get("path")
                            for m in group
                            if m.get("_id") != newest.get("_id")
                        ],
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            consolidated_count += 1

        return consolidated_count