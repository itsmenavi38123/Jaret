from collections import Counter

from app.db import get_collection
from app.models.org_playbook import OrgPlaybook
from app.services.org_playbook_service import OrgPlaybookService


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

        memories = await self.customer_memory.find(
            {
                "observation_type": "pattern"
            }
        ).to_list(
            length=None
        )

        pattern_counter = Counter()

        for memory in memories:

            content = memory.get(
                "content"
            )

            if content:
                pattern_counter[
                    content
                ] += 1

        created = 0

        for content, count in pattern_counter.items():

            if count < 2:
                continue

            path = (
                "/playbooks/patterns/"
                f"{abs(hash(content))}.json"
            )

            existing = await self.playbook_service.get_by_path(
                path
            )

            if existing:
                continue

            entry = OrgPlaybook(
                path=path,
                source_type="cross_customer_pattern",
                observation_type="pattern",
                content=content,
                supporting_data={
                    "occurrence_count": count
                },
                confidence="high",
                tags=[
                    "playbook",
                    "cross_customer_learning"
                ]
            )

            await self.playbook_service.create_entry(
                entry
            )

            created += 1

        return created