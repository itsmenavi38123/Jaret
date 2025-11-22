# backend/app/routes/ai_opportunities.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.routes.auth.auth import get_current_user
from app.db import get_collection
from app.services.research_scout_service import ResearchScoutService


router = APIRouter(tags=["ai-opportunities"])
research_scout = ResearchScoutService()


async def web_search(search_term: str, recency_days: int = 30, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Web search helper function that performs real web searches.
    Integrates with web search APIs to find opportunities.
    
    This function is called by the Research Scout service to perform actual web searches
    for opportunities, events, RFPs, grants, etc.
    """
    import os
    import httpx
    from datetime import datetime, timedelta
    
    # Priority 1: Use Tavily API if available (best for structured results)
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": search_term,
                        "max_results": max_results,
                        "search_depth": "advanced",
                        "include_answer": False,
                        "include_raw_content": False,
                    },
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    formatted = []
                    for r in results:
                        formatted.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", r.get("raw_content", "")),
                            "date": r.get("published_date"),
                        })
                    if formatted:
                        return formatted
        except Exception as e:
            print(f"Tavily search error: {e}")
    
    # Priority 2: Use Serper API if available (Google search results)
    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    json={
                        "q": search_term,
                        "num": max_results,
                    },
                    headers={
                        "X-API-KEY": serper_key,
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("organic", [])
                    formatted = []
                    for r in results:
                        formatted.append({
                            "title": r.get("title", ""),
                            "url": r.get("link", ""),
                            "snippet": r.get("snippet", ""),
                            "date": r.get("date"),
                        })
                    if formatted:
                        return formatted
        except Exception as e:
            print(f"Serper search error: {e}")
    
    # Priority 3: Use DuckDuckGo (no API key needed, but limited)
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            # Use DuckDuckGo Instant Answer API
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": search_term,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if response.status_code == 200:
                data = response.json()
                # DuckDuckGo returns limited results, format what we can
                results = []
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading", search_term),
                        "url": data.get("AbstractURL", ""),
                        "snippet": data.get("AbstractText", ""),
                        "date": None,
                    })
                # Also try web search via DuckDuckGo HTML
                html_response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": search_term},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                # Basic HTML parsing would go here
                # For now, return what we have
                if results:
                    return results
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
    
    # If all searches fail, return empty - service will use fallback
    return []


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

