# backend/app/routes/ai_scenarios.py
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.routes.auth.auth import get_current_user
from app.db import get_collection
from app.models.scenario_models import ScenarioRequest, ScenarioResponse
from app.services.orchestrator_service import OrchestratorService


router = APIRouter(tags=["ai-scenarios"])
orchestrator = OrchestratorService()


@router.post("/full", response_model=ScenarioResponse)
async def scenario_planning_full(
    request: ScenarioRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    LightSignal Scenario Planning Lab - Full Analysis
    
    Accepts free-text scenario queries and returns:
    - Classified scenario type
    - Research-backed assumptions with sources
    - Financial KPIs (ROI, IRR, Payback, DSCR, ICR, Runway)
    - Advisor recommendations
    - Visual data for charts
    - Math explanations
    
    Example queries:
    - "Hire another HVAC tech at $65k"
    - "Buy a new food truck for $80k"
    - "Raise prices by 10%"
    - "Open a second location in Tampa"
    """
    try:
        user_id = current_user["id"]
        
        # Fetch business profile
        business_profiles = get_collection("business_profiles")
        business_profile = await business_profiles.find_one({"user_id": user_id})
        
        # Fetch opportunities profile
        opportunities_profiles = get_collection("opportunities_profiles")
        opportunities_profile = await opportunities_profiles.find_one({"user_id": user_id})
        
        # Fetch baseline financials from QuickBooks
        # Use the optimized dashboard KPI fetch we just built to get real-time snapshot
        from app.services.quickbooks_financial_service import quickbooks_financial_service
        
        try:
            # We want: Revenue (annualized?), Cash, Net Margin, Runway
            # get_financial_overview is heavy, but we need details for scenario planning.
            # However, for speed/stability, let's use the lighter KPI source OR handle failure gracefully.
            # "full" analysis might justify the heavier call, but let's stick to essential KPIs data + Balance Sheet checks if needed.
            
            # Use get_dashboard_kpis for speed + essential liquidity/profit metrics
            kpis_data = await quickbooks_financial_service.get_dashboard_kpis(user_id)
            
            # Map to structure expected by FinanceAnalyst
            baseline_financials = {
                "revenue_monthly": kpis_data.get("revenue_mtd", 0.0),
                "net_margin_pct": kpis_data.get("net_margin_pct", 0.0),
                "cash_on_hand": kpis_data.get("cash", 0.0),
                "runway_months": kpis_data.get("runway_months", 0.0),
                "burn_rate": 0.0, # Not strictly returned by new kpi method but implied by runway. 
                # If we need more (e.g. debt), we might need extended fetch. For now this is better than empty.
            }
        except Exception as e:
            print(f"Failed to fetch baseline financials for scenario: {e}")
            baseline_financials = {}
        
        # Call Orchestrator
        result = await orchestrator.orchestrate_scenario_planning(
            query=request.query,
            user_id=user_id,
            business_profile=business_profile,
            opportunities_profile=opportunities_profile,
            baseline_financials=baseline_financials,
        )
        
        # Return strict JSON
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(result),
            media_type="application/json",
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
            media_type="application/json",
        )
