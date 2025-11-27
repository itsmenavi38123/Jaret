# backend/app/services/weather_service.py
"""
Weather Intelligence Service
Provides weather forecasts and historical data for demand forecasting
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import httpx


class WeatherService:
    """
    Weather intelligence service for demand forecasting.
    Integrates with OpenWeatherMap API.
    """
    
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    async def get_weather_forecast(
        self,
        lat: float,
        lng: float,
        days: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Get weather forecast for location.
        
        Args:
            lat: Latitude
            lng: Longitude
            days: Number of days to forecast (max 14)
        
        Returns:
            List of daily weather forecasts
        """
        if not self.api_key:
            print("Warning: OPENWEATHER_API_KEY not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use forecast endpoint (5-day/3-hour forecast)
                url = f"{self.base_url}/forecast"
                params = {
                    "lat": lat,
                    "lon": lng,
                    "appid": self.api_key,
                    "units": "imperial",  # Fahrenheit
                    "cnt": min(days * 8, 40)  # 8 forecasts per day, max 40
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_forecast(data)
                else:
                    print(f"Weather API error: {response.status_code}")
                    return []
        
        except Exception as e:
            print(f"Weather API exception: {e}")
            return []
    
    def _parse_forecast(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse OpenWeatherMap forecast response"""
        forecasts = []
        daily_data = {}
        
        # Group 3-hour forecasts by day
        for item in data.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            date_key = dt.date()
            
            if date_key not in daily_data:
                daily_data[date_key] = []
            
            daily_data[date_key].append({
                "temp": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "temp_min": item["main"]["temp_min"],
                "temp_max": item["main"]["temp_max"],
                "pressure": item["main"]["pressure"],
                "humidity": item["main"]["humidity"],
                "weather": item["weather"][0]["main"],
                "weather_desc": item["weather"][0]["description"],
                "clouds": item["clouds"]["all"],
                "wind_speed": item["wind"]["speed"],
                "wind_deg": item["wind"].get("deg", 0),
                "pop": item.get("pop", 0) * 100,  # Probability of precipitation
                "rain": item.get("rain", {}).get("3h", 0),
                "snow": item.get("snow", {}).get("3h", 0),
            })
        
        # Aggregate to daily forecasts
        for date_key, day_items in sorted(daily_data.items()):
            forecasts.append({
                "date": date_key.isoformat(),
                "temp_avg": sum(d["temp"] for d in day_items) / len(day_items),
                "temp_min": min(d["temp_min"] for d in day_items),
                "temp_max": max(d["temp_max"] for d in day_items),
                "humidity": sum(d["humidity"] for d in day_items) / len(day_items),
                "wind_speed": sum(d["wind_speed"] for d in day_items) / len(day_items),
                "precipitation_prob": max(d["pop"] for d in day_items),
                "conditions": max(day_items, key=lambda x: x["clouds"])["weather"],
                "description": max(day_items, key=lambda x: x["clouds"])["weather_desc"],
            })
        
        return forecasts
    
    async def calculate_weather_influence(
        self,
        weather_forecast: List[Dict[str, Any]],
        business_type: str,
        historical_correlation: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate weather influence on demand.
        
        Args:
            weather_forecast: Weather forecast data
            business_type: Type of business (affects weather sensitivity)
            historical_correlation: Historical weather-sales correlation data
        
        Returns:
            List of weather influence scores by date
        """
        influences = []
        
        # Weather-sensitive business types
        outdoor_businesses = [
            "food truck", "mobile food", "landscaping", "construction",
            "outdoor events", "tourism", "recreation"
        ]
        
        is_weather_sensitive = any(
            btype in business_type.lower() 
            for btype in outdoor_businesses
        )
        
        for forecast in weather_forecast:
            # Calculate impact score based on conditions
            impact_score = 0.0
            explanation_parts = []
            
            temp = forecast["temp_avg"]
            precip = forecast["precipitation_prob"]
            wind = forecast["wind_speed"]
            
            if is_weather_sensitive:
                # Temperature impact (ideal range: 55-85°F)
                if 55 <= temp <= 85:
                    temp_impact = 0.1
                    explanation_parts.append(f"favorable temp ({temp:.0f}°F)")
                elif temp < 45 or temp > 95:
                    temp_impact = -0.2
                    explanation_parts.append(f"extreme temp ({temp:.0f}°F)")
                else:
                    temp_impact = -0.05
                    explanation_parts.append(f"suboptimal temp ({temp:.0f}°F)")
                
                impact_score += temp_impact
                
                # Precipitation impact
                if precip < 20:
                    precip_impact = 0.05
                    explanation_parts.append("low rain chance")
                elif precip < 50:
                    precip_impact = -0.1
                    explanation_parts.append(f"{precip:.0f}% rain chance")
                else:
                    precip_impact = -0.25
                    explanation_parts.append(f"high rain chance ({precip:.0f}%)")
                
                impact_score += precip_impact
                
                # Wind impact
                if wind > 25:
                    wind_impact = -0.15
                    explanation_parts.append(f"high winds ({wind:.0f} mph)")
                elif wind > 15:
                    wind_impact = -0.05
                    explanation_parts.append(f"moderate winds ({wind:.0f} mph)")
                else:
                    wind_impact = 0.0
                
                impact_score += wind_impact
            else:
                # Non-weather-sensitive businesses have minimal impact
                impact_score = 0.0
                explanation_parts.append("minimal weather impact for this business type")
            
            # Apply historical correlation if available
            if historical_correlation:
                correlation_factor = historical_correlation.get("weather_sensitivity", 1.0)
                impact_score *= correlation_factor
            
            influences.append({
                "date": forecast["date"],
                "temperature": temp,
                "precipitation_prob": precip,
                "wind_speed": wind,
                "conditions": forecast["conditions"],
                "impact_score": max(-1.0, min(1.0, impact_score)),  # Clamp to [-1, 1]
                "explanation": ", ".join(explanation_parts) if explanation_parts else "neutral weather impact"
            })
        
        return influences
    
    async def get_severe_alerts(
        self,
        lat: float,
        lng: float
    ) -> List[Dict[str, Any]]:
        """
        Get severe weather alerts for location.
        
        Args:
            lat: Latitude
            lng: Longitude
        
        Returns:
            List of weather alerts
        """
        if not self.api_key:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use One Call API for alerts (requires different endpoint)
                url = "https://api.openweathermap.org/data/3.0/onecall"
                params = {
                    "lat": lat,
                    "lon": lng,
                    "appid": self.api_key,
                    "exclude": "minutely,hourly,daily"
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("alerts", [])
                else:
                    return []
        
        except Exception as e:
            print(f"Weather alerts exception: {e}")
            return []
