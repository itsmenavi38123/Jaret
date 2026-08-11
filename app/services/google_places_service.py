import os
import httpx
from typing import Dict, Any, List, Optional

# Consumer-facing place types (Places API "New" type taxonomy) used to filter
# Nearby Search results so the active-POI density count reflects walk-in/consumer
# frontage only — not banks, back-offices, garages, or residential lobbies.
CONSUMER_FACING_TYPES = [
    "restaurant", "cafe", "bar", "bakery", "meal_takeaway", "meal_delivery",
    "store", "clothing_store", "shoe_store", "jewelry_store", "book_store",
    "grocery_store", "supermarket", "convenience_store", "shopping_mall",
    "beauty_salon", "hair_care", "spa", "gym", "movie_theater",
    "night_club", "amusement_park", "bowling_alley", "florist",
    "furniture_store", "electronics_store", "pet_store", "liquor_store",
]


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

    async def get_photo_base64(self, photo_name: str, max_height: int = 800) -> Optional[str]:
        """Fetch Place Photo and return as base64 string."""
        import base64
        if not self.api_key:
            return None
        url = f"{self.base_url}/{photo_name}/media?key={self.api_key}&maxHeightPx={max_height}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode("utf-8")
        return None

    async def get_street_view_metadata(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """Get Street View metadata to verify if pano coverage exists."""
        if not self.api_key:
            return None
        url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&key={self.api_key}"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
        return None

    async def get_street_view_image_base64(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """Fetch Street View Static Image if coverage exists. Returns {"base64", "capture_date"}
        so downstream staleness checks (skill §2, §4.1c) can see how old the image is —
        never just the raw bytes on their own."""
        import base64
        if not self.api_key:
            return None
        meta = await self.get_street_view_metadata(lat, lng)
        if not meta or meta.get("status") != "OK":
            return None

        url = f"https://maps.googleapis.com/maps/api/streetview?size=800x600&location={lat},{lng}&key={self.api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return {
                    "base64": base64.b64encode(response.content).decode("utf-8"),
                    "capture_date": meta.get("date"),
                }
        return None

    async def search_nearby(self, lat: float, lng: float, radius: float) -> List[Dict[str, Any]]:
        """Perform a Places Nearby Search using Google Places API (New), filtered to
        consumer-facing categories so density counts reflect walk-in frontage, not
        banks/back-offices/garages/residential (skill §5.1)."""
        if not self.api_key:
            return []
        url = f"{self.base_url}/places:searchNearby"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.primaryType,places.businessStatus",
        }
        payload = {
            "includedTypes": CONSUMER_FACING_TYPES,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": lat,
                        "longitude": lng
                    },
                    "radius": radius
                }
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("places", [])
        return []

google_places_service = GooglePlacesService()