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
        return {
            "_id": str(memory["_id"]) if memory.get("_id") else None,
            "content": memory.get("content"),
            "observation_type": memory.get("observation_type"),
            "agent_name": memory.get("agent_name"),
            "confidence": memory.get("confidence"),
            "created_at": memory.get("created_at").isoformat() if isinstance(memory.get("created_at"), datetime) else memory.get("created_at"),
            "outdated": memory.get("outdated", False)
        }

    async def get_customer_memories(
        self,
        user_id: str,
        query: str | None = None,
        living_summary: bool = True,
        show_outdated: bool = False,
        show_seeded_backfilled: bool = False,
        page: int = 1,
        page_size: int = 10,
        observation_type: str | None = None,
        agent_name: str | None = None,
        tags: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ):

        filters = {
            "user_id": user_id
        }

        # Exclude living summary document if living_summary is False
        if not living_summary:
            filters["observation_type"] = {"$ne": "living_summary"}

        # Exclude outdated memories if show_outdated is False
        if not show_outdated:
            filters["outdated"] = {"$ne": True}

        # Exclude seeded/backfilled memories if show_seeded_backfilled is False
        if not show_seeded_backfilled:
            filters["seed"] = {"$ne": True}
            filters["backfilled"] = {"$ne": True}

        if query:
            filters["content"] = {
                "$regex": query,
                "$options": "i"
            }

        # Observation Type mapping
        if observation_type and observation_type != "All types":
            obs_type_lower = observation_type.lower()
            if obs_type_lower == "observation":
                filters["observation_type"] = {"$in": ["observation", "metric_observation"]}
            elif obs_type_lower == "correction":
                filters["observation_type"] = "correction"
            elif obs_type_lower == "learning":
                filters["observation_type"] = "learning"
            else:
                filters["observation_type"] = observation_type

        # Agent Name mapping
        if agent_name and agent_name != "All agents":
            agent_lower = agent_name.lower()
            if agent_lower == "financial analyst":
                filters["agent_name"] = {"$in": ["financial_analyst", "finance_analyst", "fa"]}
            elif agent_lower == "demand forecast":
                filters["agent_name"] = {"$in": ["demand_forecast", "df"]}
            elif agent_lower == "orchestrator":
                filters["agent_name"] = "orchestrator"
            elif agent_lower == "opportunity prep":
                filters["agent_name"] = {"$in": ["opportunity_prep", "prep_agent"]}
            elif agent_lower == "dia":
                filters["agent_name"] = {"$in": ["dia", "dia_agent"]}
            else:
                filters["agent_name"] = agent_name

        if tags:
            filters["tags"] = {
                "$in": tags
            }

        if start_date or end_date:

            filters["created_at"] = {}

            if start_date:
                filters["created_at"]["$gte"] = start_date

            if end_date:
                filters["created_at"]["$lte"] = end_date

        skip = (page - 1) * page_size

        total_count = await self.collection.count_documents(
            filters
        )

        cursor = (
            self.collection
            .find(filters)
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

        from uuid import uuid4
        new_memory["_id"] = str(uuid4())

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
        try:
            from bson import ObjectId
            id_filter = {"$or": [{"_id": memory_id}, {"_id": ObjectId(memory_id)}]}
        except Exception:
            id_filter = {"_id": memory_id}

        await self.collection.delete_one(id_filter)

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