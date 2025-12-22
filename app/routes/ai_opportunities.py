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
    Web search helper function using Gemini's built-in web search (grounding).
    No external search APIs needed - uses Gemini's grounding capability.
    
    This function is called by the Research Scout service to perform actual web searches
    for opportunities, events, RFPs, grants, etc.
    """
    import os
    import google.generativeai as genai
    from datetime import datetime, timedelta
    
    try:
        # Configure Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            print("GEMINI_API_KEY not found, cannot perform web search")
            return []
        
        genai.configure(api_key=gemini_api_key)
        
        # Use Gemini with grounding (web search)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Build search prompt
        search_prompt = f"""Search the web for: {search_term}

Find up to {max_results} relevant, recent results.
Focus on official sources, event platforms, government portals, and reputable sites.

Return ONLY a JSON array of results in this exact format:
[
  {{
    "title": "Result title",
    "url": "https://example.com/page",
    "snippet": "Brief description or excerpt",
    "date": "YYYY-MM-DD or null"
  }}
]

CRITICAL: Return ONLY the JSON array, no other text."""

        # Generate with grounding enabled
        response = model.generate_content(
            search_prompt,
            tools='google_search_retrieval'  # Enable web search grounding
        )
        
        # Parse response
        if response and response.text:
            import json
            import re
            
            # Extract JSON from response
            text = response.text.strip()
            
            # Try to find JSON array in response
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    results = json.loads(json_str)
                    
                    # Validate and clean results
                    formatted = []
                    for r in results[:max_results]:
                        if isinstance(r, dict) and r.get("url"):
                            formatted.append({
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "snippet": r.get("snippet", ""),
                                "date": r.get("date"),
                            })
                    
                    if formatted:
                        return formatted
                except json.JSONDecodeError as e:
                    print(f"Failed to parse Gemini search JSON: {e}")
            
            # If JSON parsing fails, try to extract from grounding metadata
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, 'grounding_chunks'):
                        results = []
                        for chunk in metadata.grounding_chunks[:max_results]:
                            if hasattr(chunk, 'web'):
                                web = chunk.web
                                results.append({
                                    "title": getattr(web, 'title', ''),
                                    "url": getattr(web, 'uri', ''),
                                    "snippet": '',
                                    "date": None,
                                })
                        if results:
                            return results
        
        print("Gemini search returned no valid results")
        return []
        
    except Exception as e:
        print(f"Gemini web search error: {e}")
        import traceback
        traceback.print_exc()
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

