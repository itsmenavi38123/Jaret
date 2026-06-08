from app.db import get_collection
from app.services.customer_memory_service import CustomerMemoryService
from app.utils.memory_factory import MemoryFactory


class MemoryBackfillService:

    def __init__(self):
        self.business_profiles = get_collection("business_profiles")
        self.scenario_chats = get_collection("scenario_chats")
        self.opportunities = get_collection("opportunities")
        self.users = get_collection("users")

        self.memory_service = CustomerMemoryService()

    async def backfill_business_profile(
        self,
        user_id: str
    ):

        profile = await self.business_profiles.find_one(
            {
                "user_id": user_id
            }
        )

        if not profile:
            return

        onboarding = profile.get(
            "onboarding_data",
            {}
        )

        memory = MemoryFactory.create_memory(
            user_id=user_id,
            observation_type="onboarding",
            content="Business profile onboarding data",
            supporting_data=onboarding,
            agent_name="backfill_service",
            session_id="business_profile_backfill",
            confidence="high",
            tags=[
                "seed",
                "business_profile"
            ],
            path=f"/memories/customer_{user_id}/seed/business_profile.json"
        )

        memory.seed = True
        memory.backfilled = True
        memory.authority = "user"

        existing_memory = await self.memory_service.get_by_path(
            memory.path
        )

        if existing_memory:
            return

        await self.memory_service.create_memory(
            memory
        )

    async def backfill_scenario_chats(
        self,
        user_id: str
    ):

        chats = await self.scenario_chats.find(
            {
                "user_id": user_id
            }
        ).to_list(
            length=None
        )

        for chat in chats:

            messages = chat.get(
                "messages",
                []
            )

            if not messages:
                continue

            chat_id = str(
                chat.get("_id")
            )

            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="decision",
                content="Historical scenario planning conversation",
                supporting_data={
                    "messages": messages,
                    "metadata": chat.get(
                        "metadata",
                        {}
                    )
                },
                agent_name="backfill_service",
                session_id=chat_id,
                confidence="medium",
                tags=[
                    "scenario_chat",
                    "backfill"
                ],
                path=f"/memories/customer_{user_id}/scenario_chats/{chat_id}.json"
            )

            memory.backfilled = True
            memory.authority = "user"

            existing_memory = await self.memory_service.get_by_path(
                memory.path
            )

            if existing_memory:
                continue

            await self.memory_service.create_memory(
                memory
            )

    async def backfill_opportunities(
        self,
        user_id: str
    ):

        opportunities = await self.opportunities.find(
            {
                "user_id": user_id
            }
        ).to_list(
            length=None
        )

        for opportunity in opportunities:

            opportunity_id = str(
                opportunity.get("_id")
            )

            summary = {
                "opportunity_name": opportunity.get(
                    "opportunity_name"
                ),
                "category": opportunity.get(
                    "category"
                ),
                "status": opportunity.get(
                    "status"
                ),
                "opportunity_type": opportunity.get(
                    "opportunity_type"
                ),
                "expected_roi": opportunity.get(
                    "expected_roi"
                ),
            }

            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="outcome",
                content="Historical opportunity record",
                supporting_data=summary,
                agent_name="backfill_service",
                session_id=opportunity_id,
                confidence="medium",
                tags=[
                    "opportunity",
                    "backfill"
                ],
                path=f"/memories/customer_{user_id}/opportunities/{opportunity_id}.json"
            )

            memory.backfilled = True
            memory.authority = "user"

            existing_memory = await self.memory_service.get_by_path(
                memory.path
            )

            if existing_memory:
                continue

            await self.memory_service.create_memory(
                memory
            )

    async def backfill_customer(
        self,
        user_id: str
    ):

        await self.backfill_business_profile(
            user_id
        )

        await self.backfill_scenario_chats(
            user_id
        )

        await self.backfill_opportunities(
            user_id
        )

    async def backfill_all_customers(
        self
    ):

        users = await self.users.find(
            {}
        ).to_list(
            length=None
        )

        for user in users:

            await self.backfill_customer(
                str(user["_id"])
            )