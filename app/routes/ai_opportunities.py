# backend/app/routes/ai_opportunities.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.routes.auth.auth import get_current_user
from app.db import get_collection
from app.services.research_scout_service import ResearchScoutService


router = APIRouter(tags=["ai-opportunities"])
research_scout = ResearchScoutService()


class OpportunitySearchRequest(BaseModel):
    query: str
    opportunity_types: Optional[List[str]] = None
    limit: Optional[int] = 10


@router.post("/search")
async def ai_opportunities_search(
    request: OpportunitySearchRequest,
    current_user: dict = Depends(get_current_user),
    mode: str = Query("live", description="Mode: 'demo' or 'live'"),
):
    """
    LightSignal Research Scout - Opportunity + Market Intelligence (JSON-only)
    
    Returns structured JSON with:
    - Market digest
    - Personalized opportunity feed with fit scoring
    - ROI estimates
    - Advisor recommendations
    - Ops Plan for high-fit opportunities
    - Industry benchmarks
    """
    try:
        user_id = current_user["id"]
        
        # Fetch business profile
        business_profiles = get_collection("business_profiles")
        business_profile = await business_profiles.find_one({"user_id": user_id})
        
        # Fetch opportunities profile
        opportunities_profiles = get_collection("opportunities_profiles")
        opportunities_profile = await opportunities_profiles.find_one({"user_id": user_id})
        
        # Call Research Scout service
        result = await research_scout.search_opportunities(
            query=request.query,
            user_id=user_id,
            business_profile=business_profile,
            opportunities_profile=opportunities_profile,
            mode=mode,
        )
        
        # Return strict JSON (no wrapper)
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


@router.get("/search")
async def ai_opportunities_search_get(
    query: str = Query(..., description="Search query"),
    opportunity_types: Optional[str] = Query(None, description="Comma-separated opportunity types"),
    limit: int = Query(10, description="Max results"),
    mode: str = Query("live", description="Mode: 'demo' or 'live'"),
    current_user: dict = Depends(get_current_user),
):
    """
    LightSignal Research Scout - GET version (JSON-only)
    """
    opp_types_list = opportunity_types.split(",") if opportunity_types else None
    
    request = OpportunitySearchRequest(
        query=query,
        opportunity_types=opp_types_list,
        limit=limit,
    )
    
    return await ai_opportunities_search(request, current_user, mode)

