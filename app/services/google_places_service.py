import os
import httpx
from typing import Dict, Any, Optional


class GooglePlacesService:

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        self.base_url = "https://places.googleapis.com/v1"

    async def find_business(
        self,
        business_name: str,
        address: str,
        ) -> Optional[Dict[str, Any]]:

        if not self.api_key:
            return None

        query = f"{business_name} {address}"

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                f"{self.base_url}/places:searchText",
                headers={
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": (
                        "places.id,"
                        "places.displayName,"
                        "places.formattedAddress,"
                        "places.location,"
                        "places.businessStatus,"
                        "places.photos"
                    ),
                },
                json={
                    "textQuery": query,
                },
            )

            response.raise_for_status()

            data = response.json()

            places = data.get("places", [])

            if not places:
                return None

            return places[0]

    async def get_place_photos():
        raise NotImplementedError(
            "Pending Google Places image acquisition flow confirmation"
        )

    async def get_street_view():
        raise NotImplementedError(
            "Pending Street View integration"
        )

    async def get_nearby_businesses():
        raise NotImplementedError(
            "Pending nearby business search implementation"
        )
google_places_service = GooglePlacesService()