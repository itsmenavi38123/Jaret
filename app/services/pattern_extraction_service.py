import json

from app.services.customer_memory_service import CustomerMemoryService
from app.services.claude_service import claude_service
from app.utils.memory_factory import MemoryFactory


class PatternExtractionService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def extract_patterns(
        self,
        user_id: str
    ):

        print(
            f"[Dreaming] Pattern Extraction Started | User={user_id}"
        )

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=500
        )

        if not memories:
            print(
                f"[Dreaming] No memories found for user {user_id}"
            )
            return 0

        if len(memories) < 5:
            print(
                f"[Dreaming] Insufficient memories for pattern extraction | User={user_id} | Memories={len(memories)}"
            )
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
                    "supporting_data": memory.get(
                        "supporting_data",
                        {}
                    ),
                    "confidence": memory.get(
                        "confidence"
                    ),
                }
            )

        print(
            f"[Dreaming] Sending {len(memory_payload)} memories to Claude"
        )

        system_prompt = """
You are LightSignal Dreaming Engine.

Your task is to analyze customer memories and identify meaningful recurring business patterns.

Look for:

- Recurring opportunity interests
- Repeated business decisions
- Repeated outcomes
- Operational themes
- Revenue or cash-flow concerns
- Growth interests
- Customer behavior trends
- Strategic focus areas

Return STRICT JSON ONLY.

{
    "patterns": [
        {
            "content": "Short pattern description",
            "confidence": "low|medium|high",
            "tags": [
                "pattern"
            ]
        }
    ]
}

Rules:

- Maximum 10 patterns.
- Only return patterns supported by explicit memory evidence.
- Do not invent information.
- Do not infer inactivity, dormancy, lack of engagement, missing goals, missing opportunities, customer maturity level, or business status from missing data.
- If there is insufficient evidence, return an empty patterns array.
- Keep pattern descriptions concise.
- Avoid duplicates.
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

            print(
                "[Dreaming] Pattern Extraction Result:"
            )
            print(result)

        except Exception as e:

            print(
                f"[Dreaming] Pattern extraction failed: {e}"
            )

            return 0

        patterns = result.get(
            "patterns",
            []
        )

        if not isinstance(
            patterns,
            list
        ):
            print(
                "[Dreaming] Invalid patterns response"
            )
            return 0

        print(
            f"[Dreaming] Claude returned {len(patterns)} patterns"
        )

        created_patterns = 0

        existing_pattern_contents = {
            (
                memory.get("content") or ""
            ).strip().lower()
            for memory in memories
            if memory.get("observation_type")
            == "pattern"
        }

        for pattern in patterns:

            content = (
                pattern.get("content") or ""
            ).strip()

            if not content:
                continue

            if (
                content.lower()
                in existing_pattern_contents
            ):
                print(
                    f"[Dreaming] Skipping existing pattern: {content}"
                )
                continue

            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="pattern",
                content=content,
                agent_name="dreaming_system",
                session_id="pattern_extraction",
                confidence=pattern.get(
                    "confidence",
                    "medium"
                ),
                tags=pattern.get(
                    "tags",
                    ["pattern"]
                ),
                supporting_data={}
            )

            memory.authority = "dreaming_pass"

            await self.memory_service.create_memory(
                memory
            )

            created_patterns += 1

            print(
                f"[Dreaming] Created pattern: {content}"
            )

        print(
            f"[Dreaming] Patterns Created: {created_patterns}"
        )

        return created_patterns