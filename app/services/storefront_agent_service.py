from app.services.claude_service import ClaudeService
from app.services.google_places_service import google_places_service
from app.services.storefront_prompt import (
    STOREFRONT_AGENT_PROMPT,
)
from app.services.storefront_skill import (
    STOREFRONT_SKILL,
)


class StorefrontAgentService:

    def __init__(self):
        self.claude = ClaudeService()
        self.google_places = google_places_service

    def _build_runtime_prompt(self) -> str:
        """
        Build runtime prompt exactly as specified:
        System Prompt + Skill loaded inline.
        """

        return (
            f"{STOREFRONT_AGENT_PROMPT}\n\n"
            f"{STOREFRONT_SKILL}"
        )

    async def _collect_location_context(
        self,
        business_name: str,
        address: str,
    ):
        """
        Collect and normalize location data from Google Places.
        """

        place = await self.google_places.find_business(
            business_name=business_name,
            address=address,
        )

        if not place:
            return None

        return {
            "place_id": place.get("id"),
            "business_status": place.get("businessStatus"),
            "display_name": (
                place.get("displayName", {})
                .get("text")
            ),
            "formatted_address": place.get("formattedAddress"),
            "location": place.get("location"),
            "photos": place.get("photos", []),
        }

    async def analyze_location(
        self,
        business_name: str,
        address: str,
        user_id: str,
        location_id: str | None = None,
    ):
        """
        Main entry point for Storefront Agent.

        Flow:

        1. Find business in Google Places
        2. Collect imagery
        3. Vision pass
        4. Reasoning pass
        5. Return structured analysis
        """

        context = await self._collect_location_context(
            business_name=business_name,
            address=address,
        )

        return {
            "user_id": user_id,
            "location_id": location_id,
            "location_context": context,
            "runtime_prompt_loaded": bool(
                self._build_runtime_prompt()
            ),
            "status": "pending_analysis",
        }


storefront_agent_service = StorefrontAgentService()