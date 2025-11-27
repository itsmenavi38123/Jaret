# backend/app/models/demand_models.py
"""
Demand Forecasting Models
Pydantic models for demand forecasting requests, responses, and data structures
"""
import datetime as dt
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime


class DateRange(BaseModel):
    """Date range for forecast"""
    start: dt.date
    end: dt.date


class ScenarioOverlay(BaseModel):
    """Optional scenario overlay from Scenario Planning Lab"""
    scenario_id: Optional[str] = None
    deltas: Optional[Dict[str, float]] = None


class ForecastRequest(BaseModel):
    """Request parameters for demand forecast"""
    date_range: DateRange
    product_filters: Optional[List[str]] = None
    location_filters: Optional[List[str]] = None
    scenario_overlay: Optional[ScenarioOverlay] = None


class ForecastProjection(BaseModel):
    """Forecast projection with confidence intervals"""
    date: dt.date
    p5: float = Field(..., description="5th percentile (pessimistic)")
    p50: float = Field(..., description="50th percentile (most likely)")
    p95: float = Field(..., description="95th percentile (optimistic)")


class ForecastDriver(BaseModel):
    """Individual driver explanation"""
    type: str = Field(..., description="weather|event|seasonal|peer|holiday")
    impact: str = Field(..., description="positive|negative|neutral")
    magnitude: float = Field(..., ge=0.0, le=1.0, description="Impact magnitude 0.0-1.0")
    explanation: str
    source: str
    event_id: Optional[str] = None
    date: Optional[dt.date] = None


class DemandKPIs(BaseModel):
    """Top-level demand forecasting KPIs"""
    forecasted_demand_30d: float = Field(..., description="Forecasted demand for next 30 days")
    event_impact_index: int = Field(..., ge=0, le=100, description="Event impact score 0-100")
    weather_influence_score: float = Field(..., description="Weather impact on demand")
    seasonality_effect: float = Field(..., description="Seasonal uplift/dip vs baseline")
    demand_risk_level: str = Field(..., description="low|medium|high")


class ForecastResponse(BaseModel):
    """Complete forecast response"""
    forecast: List[ForecastProjection]
    kpis: DemandKPIs
    drivers: List[ForecastDriver]
    scenario_lab_link: str = "/api/ai/scenarios/full?preset=demand"
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall forecast confidence")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class EventImpact(BaseModel):
    """Event impact scoring"""
    event_id: str
    event_title: str
    event_date: date
    event_type: str
    expected_impact: float = Field(..., description="Expected revenue/demand impact")
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str = "Opportunities tab"


class WeatherInfluence(BaseModel):
    """Weather impact on demand"""
    date: date
    temperature: float
    precipitation_prob: float
    wind_speed: float
    conditions: str
    impact_score: float = Field(..., description="Impact on demand (-1.0 to 1.0)")
    explanation: str


class SeasonalityEffect(BaseModel):
    """Seasonal patterns and uplift/dip"""
    period: str = Field(..., description="month|quarter|season")
    baseline: float
    seasonal_factor: float = Field(..., description="Multiplier vs baseline")
    historical_pattern: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class PeerTrend(BaseModel):
    """Industry peer trends and benchmarks"""
    metric: str
    peer_median: float
    region: str
    trend: str = Field(..., description="growing|stable|declining")
    source: str
    sample_note: str


class DriverDetailsResponse(BaseModel):
    """Detailed driver explanations response"""
    drivers: List[ForecastDriver]
    event_impacts: Optional[List[EventImpact]] = None
    weather_influences: Optional[List[WeatherInfluence]] = None
    seasonality_effects: Optional[List[SeasonalityEffect]] = None
    peer_trends: Optional[List[PeerTrend]] = None
