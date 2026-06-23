from app.services.customer_memory_service import CustomerMemoryService
from app.services.claude_service import claude_service
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

        if not patterns:
            return 0

        pattern_payload = []

        for pattern in patterns:

            pattern_payload.append(
                {
                    "content": pattern.get(
                        "content"
                    ),
                    "confidence": pattern.get(
                        "confidence"
                    ),
                    "tags": pattern.get(
                        "tags",
                        []
                    )
                }
            )

        system_prompt = """
You are LightSignal Dreaming Engine.

Your task is to analyze business patterns and derive higher-level learnings.

A learning should represent:

- Owner tendencies
- Business operating habits
- Strategic preferences
- Risk sensitivities
- Growth behavior
- Opportunity preferences
- Operational characteristics

Return STRICT JSON ONLY.

{
    "learnings": [
        {
            "content": "Business learning",
            "confidence": "low|medium|high",
            "tags": [
                "learning"
            ]
        }
    ]
}

Rules:

- Maximum 10 learnings.
- Only derive learnings supported by the supplied patterns.
- Do not invent facts.
- Avoid duplicate learnings.
- Keep learnings concise and actionable.
"""

        try:

            result = await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content={
                    "patterns": pattern_payload
                },
                temperature=0.2,
                max_tokens=3000,
            )

        except Exception as e:

            return 0

        learnings = result.get(
            "learnings",
            []
        )

        if not isinstance(
            learnings,
            list
        ):
            return 0

        created = 0

        existing_learning_contents = {
            (
                memory.get("content") or ""
            ).strip().lower()
            for memory in memories
            if memory.get("observation_type")
            == "learning"
        }

        for learning in learnings:

            content = (
                learning.get("content") or ""
            ).strip()

            if not content:
                continue

            if (
                content.lower()
                in existing_learning_contents
            ):
                continue

            path = (
                f"/memories/customer_{user_id}/learning/"
                f"{self._slugify(content)}"
            )

            existing = await self.memory_service.get_by_path(
                path=path
            )

            if existing:
                continue

            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="learning",
                content=content,
                authority="dreaming_pass",
                confidence=learning.get(
                    "confidence",
                    "medium"
                ),
                tags=learning.get(
                    "tags",
                    ["learning"]
                ),
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