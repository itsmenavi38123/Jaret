from datetime import datetime

from app.models.customer_memory import CustomerMemory
from app.services.customer_memory_service import CustomerMemoryService


class MemoryToolService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def view(
        self,
        path: str
    ):

        memory = await self.memory_service.get_by_path(
            path
        )

        if memory:
            return {
                "type": "file",
                "path": path,
                "content": memory.get(
                    "content",
                    ""
                )
            }

        memories = await self.memory_service.get_memories_by_path_prefix(
            path
        )

        return {
            "type": "directory",
            "path": path,
            "items": [
                memory.get("path")
                for memory in memories[:100]
            ]
        }

    async def create(
        self,
        user_id: str,
        path: str,
        content: str,
        observation_type: str = "memory",
        agent_name: str = "memory_tool",
        confidence: str = "high"
    ):

        existing = await self.memory_service.get_by_path(
            path
        )

        if existing:
            raise ValueError(
                f"Memory already exists: {path}"
            )

        if path.endswith(
            "_summary.md"
        ):
            observation_type = (
                "living_summary"
            )

        memory = CustomerMemory(
            user_id=user_id,
            path=path,
            observation_type=observation_type,
            content=content,
            agent_name=agent_name,
            confidence=confidence
        )

        return await self.memory_service.create_memory(
            memory
        )

    async def str_replace(
        self,
        path: str,
        old_str: str,
        new_str: str
    ):

        memory = await self.memory_service.get_by_path(
            path
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        content = memory.get(
            "content",
            ""
        )

        if old_str not in content:
            raise ValueError(
                "Target string not found"
            )

        if content.count(old_str) != 1:
            raise ValueError(
                "Target string must appear exactly once"
            )

        updated_content = content.replace(
            old_str,
            new_str,
            1
        )

        await self.memory_service.collection.update_one(
            {
                "_id": memory["_id"]
            },
            {
                "$set": {
                    "content": updated_content,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return True

    async def insert(
        self,
        path: str,
        insert_after: str,
        content: str
    ):

        memory = await self.memory_service.get_by_path(
            path
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        existing_content = memory.get(
            "content",
            ""
        )

        if insert_after not in existing_content:
            raise ValueError(
                "Insert location not found"
            )

        updated_content = existing_content.replace(
            insert_after,
            insert_after + "\n" + content,
            1
        )

        await self.memory_service.collection.update_one(
            {
                "_id": memory["_id"]
            },
            {
                "$set": {
                    "content": updated_content,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return True

    async def rename(
        self,
        old_path: str,
        new_path: str
    ):

        memory = await self.memory_service.get_by_path(
            old_path
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        existing = await self.memory_service.get_by_path(
            new_path
        )

        if existing:
            raise ValueError(
                f"Memory already exists: {new_path}"
            )

        await self.memory_service.collection.update_one(
            {
                "_id": memory["_id"]
            },
            {
                "$set": {
                    "path": new_path,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return True

    async def delete(
        self,
        path: str
    ):

        memory = await self.memory_service.get_by_path(
            path
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        await self.memory_service.mark_outdated(
            memory["_id"]
        )

        return True


memory_tool_service = MemoryToolService()