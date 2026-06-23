from app.services.customer_memory_service import CustomerMemoryService
from app.services.customer_summary_service import CustomerSummaryService
from app.services.claude_service import claude_service


class DreamingService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()
        self.summary_service = CustomerSummaryService()

    async def run_customer_dreaming(
        self,
        user_id: str
    ):

        memories = await self.memory_service.get_memory_by_user(
            user_id=user_id,
            limit=500
        )

        if not memories:
            return ""

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
                    ),
                    "supporting_data": memory.get(
                        "supporting_data",
                        {}
                    ),
                }
            )

        system_prompt = """
You are the LightSignal Dreaming Engine.

Your task is to generate a long-term customer memory summary.

The summary should help future AI agents quickly understand:

- Business profile
- Business goals
- Strategic priorities
- Major decisions
- Opportunity history
- Important patterns
- Key learnings
- Behavioral tendencies
- Risks
- Growth interests

Generate a concise but information-dense markdown summary.

Requirements:

- Use markdown.
- Start with "# Customer Memory Summary".
- Keep under 1500 words.
- Only use information supported by memories.
- Do not invent facts.
- Organize information into logical sections.
- Focus on future agent usefulness.

Return STRICT JSON ONLY.

{
    "summary": "markdown summary"
}
"""

        try:

            result = await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content={
                    "memories": memory_payload
                },
                temperature=0.2,
                max_tokens=4000,
            )

        except Exception as e:

            return ""

        summary = result.get(
            "summary",
            ""
        )

        if not isinstance(
            summary,
            str
        ):
            return ""

        summary = summary.strip()

        if not summary:
            return ""

        existing = await self.summary_service.get_summary(
            user_id
        )

        if existing:

            await self.summary_service.update_summary(
                user_id=user_id,
                content=summary
            )

        else:

            await self.summary_service.create_summary(
                user_id=user_id,
                content=summary
            )

        return summary