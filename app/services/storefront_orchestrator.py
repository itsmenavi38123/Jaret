from app.services.storefront_agent_service import (
    storefront_agent_service,
)


class StorefrontOrchestrator:

    def __init__(self):
        self.agent = storefront_agent_service

    async def run_for_location(
        self,
        user_id: str,
        business_name: str,
        address: str,
        location_id: str,
    ):

        analysis = await self.agent.analyze_location(
            business_name=business_name,
            address=address,
            user_id=user_id,
            location_id=location_id,
        )

        return analysis

    async def write_learnings(
        self,
        user_id: str,
        location_id: str,
        analysis: dict,
    ):
        pass

    async def supersede_previous_reads(
        self,
        user_id: str,
        location_id: str,
    ):
        pass


storefront_orchestrator = StorefrontOrchestrator()