from app.db import get_collection
from app.models.org_playbook import OrgPlaybook
from app.services.org_playbook_service import OrgPlaybookService
from app.services.claude_service import claude_service


class OrgPlaybookGenerationService:

    def __init__(self):
        self.customer_memory = get_collection(
            "customer_memory"
        )

        self.playbook_service = (
            OrgPlaybookService()
        )

    async def generate_playbook_entries(
        self
    ):

        print(
            "[Dreaming] Org Playbook Generation Started"
        )

        memories = await self.customer_memory.find(
            {
                "observation_type": {
                    "$in": [
                        "pattern",
                        "learning",
                        "behavior_pattern"
                    ]
                },
                "outdated": False
            }
        ).to_list(
            length=1000
        )

        if not memories:
            print(
                "[Dreaming] No memories available for playbook generation"
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
                    "confidence": memory.get(
                        "confidence"
                    ),
                    "tags": memory.get(
                        "tags",
                        []
                    )
                }
            )

        print(
            f"[Dreaming] Sending {len(memory_payload)} memories to Claude"
        )

        system_prompt = """
You are the LightSignal Dreaming Engine.

Your task is to identify cross-customer business learnings.

Analyze all supplied memories and discover patterns that appear across multiple businesses.

Focus on:

- recurring business risks
- recurring growth opportunities
- operational best practices
- strategic behavior patterns
- customer acquisition trends
- financial management patterns
- decision-making tendencies

Return STRICT JSON ONLY.

{
    "playbook_entries": [
        {
            "content": "Cross-customer learning",
            "confidence": "low|medium|high",
            "tags": [
                "playbook",
                "cross_customer_learning"
            ]
        }
    ]
}

Rules:

- Maximum 20 entries.
- Only include insights supported by supplied memories.
- Do not invent information.
- Avoid duplicates.
- Keep entries concise and actionable.
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

            print(
                "[Dreaming] Org Playbook Result:"
            )
            print(result)

        except Exception as e:

            print(
                f"[Dreaming] Org playbook generation failed: {e}"
            )

            return 0

        entries = result.get(
            "playbook_entries",
            []
        )

        if not isinstance(
            entries,
            list
        ):
            print(
                "[Dreaming] Invalid playbook response"
            )
            return 0

        print(
            f"[Dreaming] Claude returned {len(entries)} playbook entries"
        )

        created = 0

        for item in entries:

            content = (
                item.get("content") or ""
            ).strip()

            if not content:
                continue

            path = (
                "/playbooks/patterns/"
                f"{abs(hash(content))}.json"
            )

            existing = await self.playbook_service.get_by_path(
                path
            )

            if existing:
                print(
                    f"[Dreaming] Playbook already exists: {path}"
                )
                continue

            entry = OrgPlaybook(
                path=path,
                source_type="cross_customer_pattern",
                observation_type="pattern",
                content=content,
                supporting_data={},
                confidence=item.get(
                    "confidence",
                    "medium"
                ),
                tags=item.get(
                    "tags",
                    [
                        "playbook",
                        "cross_customer_learning"
                    ]
                )
            )

            await self.playbook_service.create_entry(
                entry
            )

            created += 1

            print(
                f"[Dreaming] Created playbook entry: {content}"
            )

        print(
            f"[Dreaming] Playbook Entries Created: {created}"
        )

        return created