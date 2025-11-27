# backend/app/services/demand_forecast_service.py
"""
Demand Forecast Analyst Service
Main service for generating demand forecasts using OpenAI agent
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, date
import json
import os
from openai import AsyncOpenAI
import holidays

from app.services.weather_service import WeatherService
from app.services.research_scout_service import ResearchScoutService
from app.services.finance_analyst_service import FinanceAnalystService
from app.models.demand_models import (
    ForecastRequest,
    ForecastResponse,
    ForecastProjection,
    ForecastDriver,
    DemandKPIs,
    EventImpact,
    WeatherInfluence,
    SeasonalityEffect,
    PeerTrend,
    DriverDetailsResponse
)


class DemandForecastService:
    """
    Demand Forecast Analyst agent using OpenAI.
    Predicts demand using historical sales, events, weather, holidays, and peer trends.
    """
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.research_scout = ResearchScoutService()
        self.finance_analyst = FinanceAnalystService()
        self.us_holidays = holidays.US()
    
    async def generate_forecast(
        self,
        request: ForecastRequest,
        user_id: str,
        business_profile: Optional[Dict[str, Any]] = None,
        opportunities_profile: Optional[Dict[str, Any]] = None,
        historical_sales: Optional[List[Dict[str, Any]]] = None,
    ) -> ForecastResponse:
        """
        Generate demand forecast with p5/p50/p95 projections.
        
        Args:
            request: Forecast request parameters
            user_id: User ID
            business_profile: Business profile data
            opportunities_profile: Opportunities profile data
            historical_sales: Historical sales data from QuickBooks/Xero
        
        Returns:
            Complete forecast response with KPIs and drivers
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Extract business context
        industry = "Unknown"
        location = {"city": "", "state": "", "lat": 0, "lng": 0}
        
        if business_profile and business_profile.get("onboarding_data"):
            onboarding = business_profile["onboarding_data"]
            industry = onboarding.get("industry", onboarding.get("business_type", "Unknown"))
        
        if opportunities_profile:
            region = opportunities_profile.get("operating_region", "")
            if region:
                parts = region.split(",")
                if len(parts) >= 2:
                    location["city"] = parts[0].strip()
                    location["state"] = parts[1].strip()
                else:
                    location["state"] = region
            
            # Get lat/lng if available
            location["lat"] = opportunities_profile.get("latitude", 0)
            location["lng"] = opportunities_profile.get("longitude", 0)
        
        # Gather forecast inputs
        event_impacts = await self._get_event_impacts(opportunities_profile, request.date_range)
        weather_influences = await self._get_weather_influences(location, industry, request.date_range)
        holiday_effects = self._get_holiday_effects(request.date_range)
        peer_trends = await self._get_peer_trends(industry, location)
        
        # Build system prompt for Demand Forecast Analyst
        system_prompt = f"""You are LightSignal Demand Forecast Analyst, an expert demand forecasting agent.

Your mission: Predict demand for the next 30 days using multiple data sources and return p5/p50/p95 projections.

📊 INPUTS

**Business Context**:
- Industry: {industry}
- Location: {location.get('city', '')}, {location.get('state', '')}
- User ID: {user_id}

**Historical Sales Data**:
{json.dumps(historical_sales[:50] if historical_sales else [], default=str)}
(Showing last 50 data points)

**Upcoming Events** (from Opportunities tab):
{json.dumps(event_impacts, default=str)}

**Weather Forecast**:
{json.dumps(weather_influences, default=str)}

**Holidays**:
{json.dumps(holiday_effects, default=str)}

**Peer Industry Trends**:
{json.dumps(peer_trends, default=str)}

**Date Range**: {request.date_range.start} to {request.date_range.end}

🎯 OUTPUT FORMAT — STRICT JSON ONLY

Return one object shaped as:

{{
  "forecast": [
    {{
      "date": "YYYY-MM-DD",
      "p5": 0.0,
      "p50": 0.0,
      "p95": 0.0
    }}
  ],
  "kpis": {{
    "forecasted_demand_30d": 0.0,
    "event_impact_index": 0-100,
    "weather_influence_score": 0.0,
    "seasonality_effect": 0.0,
    "demand_risk_level": "low|medium|high"
  }},
  "drivers": [
    {{
      "type": "weather|event|seasonal|peer|holiday",
      "impact": "positive|negative|neutral",
      "magnitude": 0.0-1.0,
      "explanation": "detailed explanation",
      "source": "data source",
      "event_id": "optional event ID",
      "date": "YYYY-MM-DD"
    }}
  ],
  "confidence": 0.0-1.0
}}

🧮 FORECASTING METHODOLOGY

1. **Baseline Calculation**:
   - Use historical sales data to establish baseline demand
   - Apply time-series analysis (moving averages, trend detection)
   - Account for day-of-week patterns

2. **Seasonality Adjustment**:
   - Detect seasonal patterns from historical data
   - Apply seasonal factors to baseline
   - Consider year-over-year growth

3. **Event Impact**:
   - Add expected uplift from upcoming events
   - Use event type, size, and historical performance
   - Weight by event fit score and confidence

4. **Weather Adjustment**:
   - Apply weather influence scores to forecast
   - Higher impact for weather-sensitive businesses
   - Consider precipitation, temperature, wind

5. **Holiday Effects**:
   - Apply holiday uplift/dip factors
   - Use historical holiday performance
   - Consider holiday type and business relevance

6. **Peer Trends**:
   - Incorporate industry growth/decline trends
   - Adjust for regional market conditions
   - Use peer benchmarks for validation

7. **Confidence Intervals**:
   - p5 = pessimistic (worst case with negative factors)
   - p50 = most likely (balanced scenario)
   - p95 = optimistic (best case with positive factors)
   - Wider intervals = higher uncertainty

8. **Risk Level**:
   - Low: p95/p5 ratio < 1.5, stable patterns
   - Medium: p95/p5 ratio 1.5-2.5, some volatility
   - High: p95/p5 ratio > 2.5, high uncertainty

⚙️ BEHAVIOR RULES

- Use ALL available data sources (sales, events, weather, holidays, peers)
- Explain each driver clearly and cite sources
- Be conservative with estimates when data is limited
- Calculate realistic confidence intervals (p95 > p50 > p5)
- Event Impact Index = weighted sum of event impacts (0-100 scale)
- Weather Influence Score = average weather impact across forecast period
- Seasonality Effect = % change vs baseline due to seasonal factors
- All monetary values should be in USD
- Dates must be in YYYY-MM-DD format
- Confidence should reflect data quality and forecast horizon

✅ QUALITY CHECK BEFORE RETURN

- Forecast array has one entry per day in date range
- p95 > p50 > p5 for all dates
- All KPIs are calculated and reasonable
- At least 3-5 drivers identified
- Confidence score reflects data availability
- Risk level matches forecast variance

JSON only (no Markdown, no prose outside fields).
"""
        
        # Call OpenAI
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate demand forecast for {request.date_range.start} to {request.date_range.end}"}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON
        try:
            result = json.loads(content)
            
            # Convert to ForecastResponse model
            forecast_response = ForecastResponse(
                forecast=[
                    ForecastProjection(
                        date=datetime.fromisoformat(f["date"]).date(),
                        p5=f["p5"],
                        p50=f["p50"],
                        p95=f["p95"]
                    )
                    for f in result["forecast"]
                ],
                kpis=DemandKPIs(**result["kpis"]),
                drivers=[
                    ForecastDriver(
                        type=d["type"],
                        impact=d["impact"],
                        magnitude=d["magnitude"],
                        explanation=d["explanation"],
                        source=d["source"],
                        event_id=d.get("event_id"),
                        date=datetime.fromisoformat(d["date"]).date() if d.get("date") else None
                    )
                    for d in result["drivers"]
                ],
                confidence=result.get("confidence", 0.7)
            )
            
            return forecast_response
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid JSON response from Demand Forecast Analyst: {e}")
    
    async def _get_event_impacts(
        self,
        opportunities_profile: Optional[Dict[str, Any]],
        date_range: Any
    ) -> List[Dict[str, Any]]:
        """Get event impacts from Opportunities tab"""
        if not opportunities_profile:
            return []
        
        # Extract saved/attending events
        saved_events = opportunities_profile.get("saved_events", [])
        
        event_impacts = []
        for event in saved_events:
            event_date_str = event.get("date")
            if not event_date_str:
                continue
            
            try:
                event_date = datetime.fromisoformat(event_date_str).date()
                
                # Check if event is in forecast range
                if date_range.start <= event_date <= date_range.end:
                    event_impacts.append({
                        "event_id": event.get("source_id", event.get("title", "unknown")),
                        "event_title": event.get("title", "Unknown Event"),
                        "event_date": event_date.isoformat(),
                        "event_type": event.get("type", "event"),
                        "expected_impact": event.get("est_revenue", 0),
                        "confidence": event.get("confidence", 0.5),
                        "fit_score": event.get("fit_score", 50)
                    })
            except (ValueError, AttributeError):
                continue
        
        return event_impacts
    
    async def _get_weather_influences(
        self,
        location: Dict[str, Any],
        industry: str,
        date_range: Any
    ) -> List[Dict[str, Any]]:
        """Get weather influences for forecast period"""
        lat = location.get("lat", 0)
        lng = location.get("lng", 0)
        
        if not lat or not lng:
            return []
        
        # Get weather forecast
        days = (date_range.end - date_range.start).days
        weather_forecast = await self.weather_service.get_weather_forecast(lat, lng, min(days, 14))
        
        # Calculate weather influence
        weather_influences = await self.weather_service.calculate_weather_influence(
            weather_forecast,
            industry
        )
        
        return weather_influences
    
    def _get_holiday_effects(self, date_range: Any) -> List[Dict[str, Any]]:
        """Get holiday effects for forecast period"""
        holiday_effects = []
        
        current_date = date_range.start
        while current_date <= date_range.end:
            if current_date in self.us_holidays:
                holiday_name = self.us_holidays.get(current_date)
                holiday_effects.append({
                    "date": current_date.isoformat(),
                    "holiday_name": holiday_name,
                    "type": "federal_holiday"
                })
            
            current_date += timedelta(days=1)
        
        return holiday_effects
    
    async def _get_peer_trends(
        self,
        industry: str,
        location: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get peer industry trends from Research Scout"""
        try:
            # Use Research Scout to get peer trends
            # This would call a new method we'll add to ResearchScoutService
            peer_data = await self.research_scout.get_peer_seasonal_trends(
                industry=industry,
                region=location.get("state", "")
            )
            return peer_data
        except Exception as e:
            print(f"Error getting peer trends: {e}")
            return []
    
    async def get_forecast_drivers(
        self,
        forecast_id: Optional[str] = None,
        date_filter: Optional[date] = None
    ) -> DriverDetailsResponse:
        """
        Get detailed driver explanations.
        
        Args:
            forecast_id: Optional forecast ID to retrieve
            date_filter: Optional date to filter drivers
        
        Returns:
            Detailed driver explanations
        """
        # This would retrieve stored forecast data
        # For now, return empty structure
        return DriverDetailsResponse(
            drivers=[],
            event_impacts=[],
            weather_influences=[],
            seasonality_effects=[],
            peer_trends=[]
        )
    
    async def calculate_demand_kpis(
        self,
        forecast_projections: List[ForecastProjection],
        drivers: List[ForecastDriver]
    ) -> DemandKPIs:
        """
        Calculate top-level demand KPIs from forecast.
        
        Args:
            forecast_projections: Forecast projections
            drivers: Forecast drivers
        
        Returns:
            Demand KPIs
        """
        # Calculate forecasted demand (sum of p50 values)
        forecasted_demand_30d = sum(f.p50 for f in forecast_projections[:30])
        
        # Calculate event impact index (0-100)
        event_drivers = [d for d in drivers if d.type == "event"]
        event_impact_index = min(100, int(sum(d.magnitude * 100 for d in event_drivers)))
        
        # Calculate weather influence score
        weather_drivers = [d for d in drivers if d.type == "weather"]
        weather_influence_score = sum(d.magnitude for d in weather_drivers) / max(1, len(weather_drivers))
        
        # Calculate seasonality effect
        seasonal_drivers = [d for d in drivers if d.type == "seasonal"]
        seasonality_effect = sum(d.magnitude for d in seasonal_drivers) / max(1, len(seasonal_drivers))
        
        # Calculate demand risk level
        if forecast_projections:
            avg_variance = sum(
                (f.p95 - f.p5) / max(1, f.p50) 
                for f in forecast_projections
            ) / len(forecast_projections)
            
            if avg_variance < 0.3:
                risk_level = "low"
            elif avg_variance < 0.6:
                risk_level = "medium"
            else:
                risk_level = "high"
        else:
            risk_level = "medium"
        
        return DemandKPIs(
            forecasted_demand_30d=forecasted_demand_30d,
            event_impact_index=event_impact_index,
            weather_influence_score=weather_influence_score,
            seasonality_effect=seasonality_effect,
            demand_risk_level=risk_level
        )
