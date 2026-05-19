from typing import Dict, Any
from app.services.opportunity_rescore_service import opportunity_rescore_service


class ProfileEventHandlerService:

    async def handle_profile_classified(
        self,
        event: Dict[str, Any],
    ):

        business_id = event.get("business_id")

        if not business_id:
            return

        await opportunity_rescore_service.rescore_by_profile_update(
            business_id=business_id,
        )


profile_event_handler_service = ProfileEventHandlerService()