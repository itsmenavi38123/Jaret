# backend/app/routes/demand_forecast.py
"""
Demand Forecasting API Routes
Endpoints for demand forecasting and driver explanations
"""
from typing import Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.routes.auth.auth import get_current_user
from app.db import get_collection
from app.models.demand_models import (
    ForecastRequest,
    ForecastResponse,
    DriverDetailsResponse,
    DateRange
)
from app.services.demand_forecast_service import DemandForecastService
from app.services.quickbooks_financial_service import quickbooks_financial_service


router = APIRouter(tags=["demand-forecast"])
demand_forecast_service = DemandForecastService()


@router.post("/forecast/demand", response_model=ForecastResponse)
async def generate_demand_forecast(
    request: ForecastRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate demand forecast with p5/p50/p95 projections.
    
    **Data Sources**:
    - Historical sales from QuickBooks/Xero
    - Events from Opportunities tab
    - Weather forecast (OpenWeatherMap)
    - Holidays calendar
    - Peer industry trends (Research Scout)
    
    **Returns**:
    - Forecast projections (p5/p50/p95)
    - Top-level KPIs (forecasted demand, event impact, weather influence, seasonality, risk)
    - Driver explanations
    - Scenario Planning Lab link for what-if analysis
    """
    try:
        user_id = current_user["id"]
        
        # Fetch business profile
        business_profiles = get_collection("business_profiles")
        business_profile = await business_profiles.find_one({"user_id": user_id})
        
        # Fetch opportunities profile
        opportunities_profiles = get_collection("opportunities_profiles")
        opportunities_profile = await opportunities_profiles.find_one({"user_id": user_id})
        
        # Fetch historical sales data from QuickBooks
        # Default to last 12 months if not specified
        if not request.date_range:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)
            request.date_range = DateRange(start=start_date, end=end_date)
        
        # Get historical sales for forecasting
        historical_start = request.date_range.start - timedelta(days=365)  # Get 1 year of history
        
        try:
            historical_sales = await quickbooks_financial_service.get_historical_sales(
                user_id=user_id,
                start_date=historical_start,
                end_date=request.date_range.start,
                granularity="monthly"
            )
        except HTTPException:
            # If QuickBooks not connected, proceed with empty historical data
            historical_sales = []
        
        # Generate forecast
        forecast_response = await demand_forecast_service.generate_forecast(
            request=request,
            user_id=user_id,
            business_profile=business_profile,
            opportunities_profile=opportunities_profile,
            historical_sales=historical_sales
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(forecast_response),
            media_type="application/json"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate demand forecast: {str(e)}"
        )


@router.get("/forecast/demand/drivers", response_model=DriverDetailsResponse)
async def get_forecast_drivers(
    forecast_id: Optional[str] = Query(None, description="Forecast ID to retrieve"),
    date_filter: Optional[date] = Query(None, description="Filter drivers by date"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get detailed driver explanations for demand forecast.
    
    **Returns**:
    - Detailed driver breakdowns (weather, events, seasonal, peer, holiday)
    - Event impacts with confidence scores
    - Weather influences by date
    - Seasonality effects
    - Peer industry trends
    
    **Use Case**: Display tooltips and detailed explanations in UI
    """
    try:
        # Get driver details
        driver_details = await demand_forecast_service.get_forecast_drivers(
            forecast_id=forecast_id,
            date_filter=date_filter
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(driver_details),
            media_type="application/json"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get forecast drivers: {str(e)}"
        )


@router.get("/forecast/demand/quick")
async def get_quick_forecast(
    days: int = Query(30, ge=7, le=90, description="Number of days to forecast"),
    current_user: dict = Depends(get_current_user),
):
    """
    Quick demand forecast for next N days (simplified endpoint).
    
    **Parameters**:
    - days: Number of days to forecast (7-90, default 30)
    
    **Returns**:
    - Simplified forecast with key KPIs
    - No detailed drivers (use /forecast/demand for full details)
    """
    try:
        user_id = current_user["id"]
        
        # Build simple request
        end_date = datetime.now().date() + timedelta(days=days)
        start_date = datetime.now().date()
        
        request = ForecastRequest(
            date_range=DateRange(start=start_date, end=end_date)
        )
        
        # Fetch profiles
        business_profiles = get_collection("business_profiles")
        business_profile = await business_profiles.find_one({"user_id": user_id})
        
        opportunities_profiles = get_collection("opportunities_profiles")
        opportunities_profile = await opportunities_profiles.find_one({"user_id": user_id})
        
        # Get historical sales
        historical_start = start_date - timedelta(days=365)
        try:
            historical_sales = await quickbooks_financial_service.get_historical_sales(
                user_id=user_id,
                start_date=historical_start,
                end_date=start_date,
                granularity="monthly"
            )
        except HTTPException:
            historical_sales = []
        
        # Generate forecast
        forecast_response = await demand_forecast_service.generate_forecast(
            request=request,
            user_id=user_id,
            business_profile=business_profile,
            opportunities_profile=opportunities_profile,
            historical_sales=historical_sales
        )
        
        # Return simplified response
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": {
                    "kpis": forecast_response.kpis,
                    "forecast_summary": {
                        "p50_total": sum(f.p50 for f in forecast_response.forecast),
                        "p5_total": sum(f.p5 for f in forecast_response.forecast),
                        "p95_total": sum(f.p95 for f in forecast_response.forecast),
                        "days": days
                    },
                    "top_drivers": forecast_response.drivers[:3],  # Top 3 drivers
                    "confidence": forecast_response.confidence
                }
            })
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quick forecast: {str(e)}"
        )
