from collections import Counter

from app.services.customer_memory_service import CustomerMemoryService
from app.services.customer_summary_service import CustomerSummaryService


class DreamingService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()
        self.summary_service = CustomerSummaryService()

    async def run_customer_dreaming(self, user_id: str):

        memories = await self.memory_service.get_memory_by_user(user_id=user_id, limit=500)

        observation_counter = Counter()

        business_name = None
        industry = None
        city = None
        state = None

        goals = []
        priorities = []

        opportunity_names = []
        patterns = []
        learnings = []
        decisions = []
        behavior_patterns = []

        for memory in memories:

            observation_type = memory.get("observation_type")

            if observation_type:
                observation_counter[observation_type] += 1

            supporting_data = memory.get("supporting_data", {})

            if observation_type == "onboarding":

                business_name = supporting_data.get("business_name")
                industry = supporting_data.get("industry_description")
                city = supporting_data.get("city")
                state = supporting_data.get("state")

                priorities = supporting_data.get("priorities", [])

                goals_12_months = supporting_data.get("goals_12_months")
                goals_3_years = supporting_data.get("goals_3_years")

                if goals_12_months:
                    goals.append(goals_12_months)

                if goals_3_years:
                    goals.append(goals_3_years)

            elif observation_type == "outcome":

                opportunity_name = supporting_data.get("opportunity_name")

                if opportunity_name:
                    opportunity_names.append(opportunity_name)

            elif observation_type == "pattern":

                content = memory.get("content")

                if content:
                    patterns.append(content)

            elif observation_type == "learning":

                content = memory.get("content")

                if content:
                    learnings.append(content)

            elif observation_type == "decision":

                content = memory.get("content")

                if content:
                    decisions.append(content)

            elif observation_type == "behavior_pattern":

                content = memory.get("content")

                if content:
                    behavior_patterns.append(content)

        summary_lines = ["# Customer Memory Summary", ""]

        if business_name:
            summary_lines.append(f"Business: {business_name}")

        if industry:
            summary_lines.append(f"Industry: {industry}")

        if city and state:
            summary_lines.append(f"Location: {city}, {state}")

        summary_lines.extend(["", "Key Priorities:"])

        for priority in priorities:
            summary_lines.append(f"- {priority}")

        summary_lines.extend(["", "Business Goals:"])

        for goal in goals:
            summary_lines.append(f"- {goal}")

        summary_lines.extend([
            "",
            "Historical Activity:",
            f"- {observation_counter.get('outcome', 0)} opportunities tracked",
            f"- {observation_counter.get('decision', 0)} scenario planning conversations"
        ])

        if opportunity_names:
            summary_lines.extend(["", "Recent Opportunities:"])
            summary_lines.extend([f"- {name}" for name in opportunity_names[:5]])

        if decisions:
            summary_lines.extend(["", "Major Decisions:"])
            summary_lines.extend([f"- {decision}" for decision in decisions[:5]])

        if patterns:
            summary_lines.extend(["", "Observed Patterns:"])
            summary_lines.extend([f"- {pattern}" for pattern in patterns[:10]])

        if learnings:
            summary_lines.extend(["", "Owner Tendencies:"])
            summary_lines.extend([f"- {learning}" for learning in learnings[:10]])

        if behavior_patterns:
            summary_lines.extend(["", "Behavior Patterns:"])
            summary_lines.extend([f"- {pattern}" for pattern in behavior_patterns[:10]])

        summary = "\n".join(summary_lines)

        existing = await self.summary_service.get_summary(user_id)

        if existing:
            await self.summary_service.update_summary(user_id=user_id, content=summary)
        else:
            await self.summary_service.create_summary(user_id=user_id, content=summary)

        return summary