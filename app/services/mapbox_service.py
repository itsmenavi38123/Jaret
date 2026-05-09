# backend/app/services/mapbox_service.py

from typing import Optional, Dict, Any
from datetime import datetime
import math
import httpx
import os


class MapboxService:

    GEOCODE_BASE_URL = "https://api.mapbox.com/search/geocode/v6/forward"
    DIRECTIONS_BASE_URL = "https://api.mapbox.com/directions/v5/mapbox/driving"

    def __init__(self):

        self.api_key = os.getenv("MAPBOX_API_KEY")

        if not self.api_key:
            raise ValueError("MAPBOX_API_KEY not found in environment")

    async def geocode_address(
        self,
        address: str
    ) -> Dict[str, Any]:

        if not address:
            return self._empty_geocode_response()

        params = {
            "q": address,
            "access_token": self.api_key,
            "limit": 1,
        }

        try:

            async with httpx.AsyncClient(timeout=15.0) as client:

                response = await client.get(
                    self.GEOCODE_BASE_URL,
                    params=params,
                )

            if response.status_code != 200:
                return self._empty_geocode_response()

            data = response.json()

            features = data.get("features", [])

            if not features:
                return self._empty_geocode_response()

            feature = features[0]

            coordinates = (
                feature.get("geometry", {})
                .get("coordinates", [])
            )

            lng = coordinates[0] if len(coordinates) > 0 else None
            lat = coordinates[1] if len(coordinates) > 1 else None

            properties = feature.get("properties", {})
            context = properties.get("context", {})

            city = (
                context.get("place", {})
                .get("name")
            )

            state = (
                context.get("region", {})
                .get("region_code")
            )

            timezone = (
                context.get("timezone", {})
                .get("name")
            )

            relevance = feature.get("relevance", 0)

            geocode_confidence = (
                "high" if relevance >= 0.5 else "low"
            )

            if not timezone and state:
                timezone = self._get_timezone_from_state(
                    state
                )

            return {
                "lat": lat,
                "lng": lng,
                "city": city,
                "state": state,
                "timezone": timezone,
                "relevance": relevance,
                "geocode_confidence": geocode_confidence,
                "success": True,
            }

        except Exception as e:

            print(f"Mapbox geocode error: {e}")

            return self._empty_geocode_response()

    async def calculate_drive_time(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        depart_at: Optional[str] = None,
    ) -> Dict[str, Any]:

        if not all([
            origin_lat,
            origin_lng,
            destination_lat,
            destination_lng,
        ]):

            return self._fallback_drive_time(
                origin_lat,
                origin_lng,
                destination_lat,
                destination_lng,
            )

        coordinates = (
            f"{origin_lng},{origin_lat};"
            f"{destination_lng},{destination_lat}"
        )

        url = f"{self.DIRECTIONS_BASE_URL}/{coordinates}"

        params = {
            "access_token": self.api_key,
            "annotations": "duration",
        }

        if depart_at:
            params["depart_at"] = depart_at

        try:

            async with httpx.AsyncClient(timeout=20.0) as client:

                response = await client.get(
                    url,
                    params=params,
                )

            if response.status_code != 200:

                return self._fallback_drive_time(
                    origin_lat,
                    origin_lng,
                    destination_lat,
                    destination_lng,
                )

            data = response.json()

            routes = data.get("routes", [])

            if not routes:

                return self._fallback_drive_time(
                    origin_lat,
                    origin_lng,
                    destination_lat,
                    destination_lng,
                )

            duration_seconds = routes[0].get("duration")

            if duration_seconds is None:

                return self._fallback_drive_time(
                    origin_lat,
                    origin_lng,
                    destination_lat,
                    destination_lng,
                )

            drive_time_minutes = round(
                duration_seconds / 60,
                2
            )

            distance_miles = self.haversine_distance_miles(
                origin_lat,
                origin_lng,
                destination_lat,
                destination_lng,
            )

            return {
                "drive_time_minutes": drive_time_minutes,
                "drive_time_is_estimated": False,
                "distance_miles": round(distance_miles, 2),
                "success": True,
            }

        except Exception as e:

            print(f"Mapbox directions error: {e}")

            return self._fallback_drive_time(
                origin_lat,
                origin_lng,
                destination_lat,
                destination_lng,
            )

    async def build_opportunity_geo(
        self,
        location_text: str,
        company_latitude: float = None,
        company_longitude: float = None,
        start_date: Optional[datetime] = None,
        opportunity_type: Optional[str] = None,
    ):

        if not location_text:
            return None

        geo_data = await self.geocode_address(
            location_text
        )

        latitude = geo_data.get("lat")
        longitude = geo_data.get("lng")

        geocode_confidence = geo_data.get(
            "geocode_confidence"
        )

        drive_time_minutes = None
        drive_time_is_estimated = False

        depart_at = None

        if (
            opportunity_type in [
                "Event",
                "Venue Residency"
            ]
            and start_date
        ):

            depart_at = start_date.replace(
                hour=7,
                minute=0,
                second=0,
                microsecond=0
            ).isoformat()

        else:

            depart_at = datetime.now().replace(
                hour=9,
                minute=0,
                second=0,
                microsecond=0
            ).isoformat()

        if (
            latitude
            and longitude
            and company_latitude
            and company_longitude
        ):

            drive_data = await self.calculate_drive_time(
                origin_lat=company_latitude,
                origin_lng=company_longitude,
                destination_lat=latitude,
                destination_lng=longitude,
                depart_at=depart_at,
            )

            drive_time_minutes = drive_data.get(
                "drive_time_minutes"
            )

            drive_time_is_estimated = drive_data.get(
                "drive_time_is_estimated",
                False
            )

        return {
            "location_text": location_text,
            "latitude": latitude,
            "longitude": longitude,
            "geocode_confidence": geocode_confidence,
            "drive_time_minutes": drive_time_minutes,
            "drive_time_is_estimated": drive_time_is_estimated,
            "depart_at": depart_at,
        }

    def haversine_distance_miles(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:

        radius_miles = 3958.8

        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)

        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)

        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(dlng / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )

        return radius_miles * c

    def _fallback_drive_time(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
    ) -> Dict[str, Any]:

        try:

            distance_miles = self.haversine_distance_miles(
                origin_lat,
                origin_lng,
                destination_lat,
                destination_lng,
            )

            estimated_minutes = (
                distance_miles / 45
            ) * 60

            return {
                "drive_time_minutes": round(
                    estimated_minutes,
                    2
                ),
                "drive_time_is_estimated": True,
                "distance_miles": round(
                    distance_miles,
                    2
                ),
                "success": True,
            }

        except Exception:

            return {
                "drive_time_minutes": None,
                "drive_time_is_estimated": True,
                "distance_miles": None,
                "success": False,
            }

    def _empty_geocode_response(
        self
    ) -> Dict[str, Any]:

        return {
            "lat": None,
            "lng": None,
            "city": None,
            "state": None,
            "timezone": None,
            "relevance": 0,
            "geocode_confidence": "low",
            "success": False,
        }

    def _get_timezone_from_state(
        self,
        state_code: str
    ) -> Optional[str]:

        timezone_map = {
            "CA": "America/Los_Angeles",
            "TX": "America/Chicago",
            "NY": "America/New_York",
            "FL": "America/New_York",
            "IL": "America/Chicago",
            "WA": "America/Los_Angeles",
            "CO": "America/Denver",
        }

        return timezone_map.get(state_code)