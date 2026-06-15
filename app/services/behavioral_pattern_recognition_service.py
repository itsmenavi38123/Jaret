from app.services.customer_memory_service import CustomerMemoryService
from app.services.claude_service import claude_service
from app.utils.memory_factory import MemoryFactory


class BehavioralPatternRecognitionService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def extract_behavior_patterns(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=500
        )

        if not memories:
            return 0

        if len(memories) < 5:
            return 0

        memory_payload = []

        for memory in memories:

            memory_payload.append(
                {
                    "observation_type": memory.get(
                        "observation_type"
                    ),
                    "content": memory.get(
                        "content"
                    ),
                    "confidence": memory.get(
                        "confidence"
                    ),
                    "tags": memory.get(
                        "tags",
                        []
                    )
                }
            )

        system_prompt = """
You are LightSignal Dreaming Engine.

Your task is to analyze customer memories and identify behavioral patterns.

Behavior patterns should focus on:

- Decision-making tendencies
- Risk tolerance
- Strategic planning behavior
- Growth behavior
- Opportunity engagement behavior
- Operational habits
- Follow-through consistency
- Financial behavior patterns

Return STRICT JSON ONLY.

{
    "behavior_patterns": [
        {
            "content": "Behavior pattern description",
            "confidence": "low|medium|high",
            "tags": [
                "behavior_pattern"
            ]
        }
    ]
}

Rules:

- Maximum 10 behavior patterns.
- Only return patterns supported by explicit memory evidence.
- Do not invent information.
- Do not infer inactivity, dormancy, lack of engagement, missing goals, missing opportunities, customer maturity level, or business status from missing data.
- Only create behavior patterns from positive evidence present in memories.
- If there is insufficient evidence, return an empty behavior_patterns array.
- Avoid duplicates.
- Keep patterns concise.

IMPORTANT:

Learnings describe what is true about the business.

Behavior patterns describe how the owner behaves, decides, prioritizes, or responds over time.
"""

        try:

            result = await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content={
                    "memories": memory_payload
                },
                temperature=0.2,
                max_tokens=3000,
            )

        except Exception as e:

            return 0

        behavior_patterns = result.get(
            "behavior_patterns",
            []
        )

        if not isinstance(
            behavior_patterns,
            list
        ):
            return 0

        created = 0

        existing_behavior_contents = {
            (
                memory.get("content") or ""
            ).strip().lower()
            for memory in memories
            if memory.get("observation_type")
            == "behavior_pattern"
        }

        for pattern in behavior_patterns:

            content = (
                pattern.get("content") or ""
            ).strip()

            if not content:
                continue

            if (
                content.lower()
                in existing_behavior_contents
            ):
                continue

            path = (
                f"/memories/customer_{user_id}/behavior/"
                f"{self._slugify(content)}"
            )

            existing = await self.memory_service.get_by_path(
                path=path
            )

            if existing:
                continue

            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="behavior_pattern",
                content=content,
                authority="dreaming_pass",
                confidence=pattern.get(
                    "confidence",
                    "medium"
                ),
                tags=pattern.get(
                    "tags",
                    ["behavior_pattern"]
                ),
                path=path
            )

            await self.memory_service.create_memory(
                memory
            )

            created += 1

        return created

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