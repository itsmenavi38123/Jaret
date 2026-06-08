from app.services.customer_memory_service import CustomerMemoryService
from app.utils.memory_factory import MemoryFactory


class MemoryLearningService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def extract_learnings(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=500
        )

        patterns = [
            memory
            for memory in memories
            if memory.get("observation_type") == "pattern"
        ]

        created = 0

        for pattern in patterns:

            content = (
                pattern.get("content") or ""
            ).lower()

            learning_text = self._derive_learning(
                content
            )

            if not learning_text:
                continue

            path = (
                f"/memories/customer_{user_id}/learning/"
                f"{self._slugify(learning_text)}"
            )

            existing = await self.memory_service.get_by_path(
                path=path
            )

            if existing:
                continue

            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="learning",
                content=learning_text,
                authority="dreaming_pass",
                confidence="medium",
                tags=["learning"],
                path=path
            )

            await self.memory_service.create_memory(
                memory
            )

            created += 1

        return created

    async def get_learning_memories(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=500
        )

        return [
            memory
            for memory in memories
            if memory.get("observation_type") == "learning"
        ]

    def _derive_learning(
        self,
        pattern_content: str
    ):

        if "festival" in pattern_content:
            return (
                "Business consistently engages with food and beverage industry events."
            )

        if "marketing" in pattern_content:
            return (
                "Owner rarely acts on marketing-related recommendations."
            )

        if "cash" in pattern_content:
            return (
                "Business is highly sensitive to cash-flow related risks."
            )

        return None

    def _slugify(
        self,
        text: str
    ):

        return (
            text.lower()
            .replace(" ", "_")
            .replace(".", "")
            .replace(",", "")
        )