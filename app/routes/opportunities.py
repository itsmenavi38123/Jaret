# backend/app/routes/opportunities.py
"""
Opportunities Overview API - Powers the entire Opportunities UI
Returns KPIs, recommended opportunities, search results, and tracked opportunities
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.routes.auth.auth import get_current_user
from app.db import get_collection
from app.services.research_scout_service import ResearchScoutService
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.agents.opportunities_agent import research_scout_opportunities

router = APIRouter(tags=["opportunities"])
research_scout = ResearchScoutService()


@router.get("/overview")
async def get_opportunities_overview(
    current_user: dict = Depends(get_current_user),
    search_query: Optional[str] = Query(None, description="Optional search query"),
):
    """
    Get complete opportunities overview for the UI.
    
    Returns:
    - KPIs (5 cards)
    - AI-Recommended opportunities
    - Search results (if search_query provided)
    - Selected & Tracked opportunities table
    """
    try:
        user_id = current_user["id"]
        
        # Fetch profiles
        business_profiles = get_collection("business_profiles")
        business_profile = await business_profiles.find_one({"user_id": user_id})
        
        opportunities_profiles = get_collection("opportunities_profiles")
        opportunities_profile = await opportunities_profiles.find_one({"user_id": user_id})
        
        # Fetch QuickBooks data for financial context
        try:
            qb_kpis = await quickbooks_financial_service.get_dashboard_kpis(user_id)
            cash = qb_kpis.get("cash", 0)
            runway_months = qb_kpis.get("runway_months", 0)
        except:
            cash = 0
            runway_months = 0
        
        # Get opportunities from Research Scout
        scout_query = search_query or "What opportunities are available for my business this month?"
        scout_result = await research_scout.search_opportunities(
            query=scout_query,
            user_id=user_id,
            business_profile=business_profile,
            opportunities_profile=opportunities_profile,
            mode="live",
        )
        
        # Transform Research Scout response to UI format
        ui_response = _transform_to_ui_format(
            scout_result, 
            user_id,
            cash,
            runway_months
        )
        
        # Add tracked/selected opportunities from database
        opportunities_collection = get_collection("opportunities")
        tracked_opps = await opportunities_collection.find({
            "user_id": user_id,
            "status": {"$in": ["Tracked", "Selected", "Applied"]}
        }).to_list(length=100)
        
        ui_response["selected_tracked"] = _format_tracked_opportunities(tracked_opps)
        
        # Add historical ROI from outcomes
        outcomes_collection = get_collection("opportunity_outcomes")
        outcomes = await outcomes_collection.find({"user_id": user_id}).to_list(length=100)
        historical_roi = _calculate_historical_roi(outcomes)
        ui_response["kpis"]["historical_roi"] = historical_roi
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(ui_response),
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
        )


@router.get("/manual-search")
async def manual_opportunities_search(
    query: str = Query(..., description="Manual search query for opportunities"),
    current_user: dict = Depends(get_current_user),
):
    """
    Search for opportunities using a manual query without requiring business profiles.

    This endpoint allows users to search for opportunities based on their own query,
    bypassing personalized business profile matching.
    """
    try:
        user_id = current_user["id"]

        # Call the research scout agent
        scout_result = research_scout_opportunities(query)

        return scout_result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
        )


@router.get("/research-scout")
async def get_research_scout_opportunities(
    current_user: dict = Depends(get_current_user),
):
    """
    Get opportunities directly from the Research Scout agent.

    Returns raw data from the opportunities_agent.research_scout function.
    """
    try:
        user_id = current_user["id"]

        # Fetch business profile
        agent_profile ={
        "business_type": "Food Truck",
        "services": ["Street food", "Catering"],
        "location": "Austin, Texas",
        "keywords": ["festival", "vendor", "grant"]
    }

        # Call the research scout agent
        scout_result = research_scout_opportunities(agent_profile)

        return scout_result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
        )


def _transform_to_ui_format(
    scout_result: Dict[str, Any],
    user_id: str,
    cash: float,
    runway_months: float
) -> Dict[str, Any]:
    """Transform Research Scout response to UI format"""
    
    opportunities_data = scout_result.get("opportunities", {})
    cards = opportunities_data.get("cards", [])
    scout_kpis = opportunities_data.get("kpis", {})
    
    # Calculate KPIs from REAL data only
    active_count = len(cards)  # Actual count from Research Scout
    total_value = sum(card.get("est_revenue", 0) for card in cards if card.get("est_revenue"))
    
    # Average fit score - only if we have cards
    avg_fit = 0
    if cards:
        fit_scores = [card.get("fit_score", 0) for card in cards if card.get("fit_score")]
        if fit_scores:
            avg_fit = sum(fit_scores) / len(fit_scores)
    
    # Event readiness - only calculate if we have event cards
    event_readiness = 0
    event_cards = [c for c in cards if c.get("type") == "event"]
    if event_cards:
        readiness_scores = [
            _calculate_event_readiness(c, cash, runway_months) 
            for c in event_cards
        ]
        event_readiness = sum(readiness_scores) / len(readiness_scores)
    
    # Transform opportunity cards
    recommended = []
    for card in cards[:10]:  # Top 10 recommendations
        recommended.append(_transform_opportunity_card(card, cash, runway_months))
    
    return {
        "kpis": {
            "active_opportunities": {
                "count": active_count,
                "new_this_week": None  # Will be calculated from database timestamps
            },
            "total_potential_value": total_value if total_value > 0 else None,
            "avg_fit_score": round(avg_fit) if avg_fit > 0 else None,
            "event_readiness_index": round(event_readiness) if event_readiness > 0 else None,
            "historical_roi": {
                "multiplier": None,  # Will be filled from database
                "sample_size": 0
            }
        },
        "recommended": recommended,
        "search_results": [],
    }


def _transform_opportunity_card(
    card: Dict[str, Any],
    cash: float,
    runway_months: float
) -> Dict[str, Any]:
    """Transform a Research Scout card to UI format"""
    
    # Parse dates
    start_date = card.get("date")
    deadline = card.get("deadline")
    
    # Calculate fit label
    fit_score = card.get("fit_score", 0)
    if fit_score >= 80:
        fit_label = "High"
    elif fit_score >= 60:
        fit_label = "Moderate"
    else:
        fit_label = "Low"
    
    # Build why_suggested from pros/cons
    why_suggested = card.get("pros", [])[:3]  # Top 3 reasons
    
    # Calculate readiness
    readiness_score = _calculate_event_readiness(card, cash, runway_months)
    if readiness_score >= 85:
        readiness_status = "On Track"
    else:
        readiness_status = "At Risk"
    
    return {
        "id": card.get("source_id", f"opp_{hash(card.get('title', ''))}"),
        "title": card.get("title", ""),
        "type": card.get("type", "event").capitalize(),
        "dates": {
            "start": start_date,
            "end": deadline or start_date,
            "display": _format_date_range(start_date, deadline)
        },
        "location": {
            "city": card.get("location", {}).get("city", ""),
            "state": card.get("location", {}).get("state", ""),
            "venue": ""
        },
        "status": None,  # Will be set from database
        "financials": {
            "est_revenue": card.get("est_revenue", 0),
            "est_cost": card.get("cost", 0),
            "expected_roi": card.get("roi_est", 0),
            "roi_basis": "based on peers" if card.get("confidence", 0) < 0.8 else "based on data"
        },
        "scoring": {
            "fit_score": fit_score,
            "fit_label": fit_label,
            "confidence": card.get("confidence", 0.5)
        },
        "why_suggested": why_suggested,
        "weather_badge": card.get("weather_badge"),
        "link": card.get("link"),
        "provider": card.get("provider"),
        "readiness": {
            "score": round(readiness_score),
            "status": readiness_status,
            "confidence": "High" if card.get("confidence", 0) > 0.7 else "Medium"
        }
    }


def _calculate_event_readiness(
    card: Dict[str, Any],
    cash: float,
    runway_months: float
) -> float:
    """
    Calculate event readiness score (0-100)
    Components: Time (25) + Weather (25) + Financial (25) + Operational (25)
    """
    score = 0
    
    # Time readiness (0-25)
    event_date = card.get("date")
    if event_date:
        try:
            from datetime import datetime
            event_dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
            days_to_event = (event_dt - datetime.now()).days
            
            if days_to_event >= 28:
                score += 25
            elif days_to_event >= 21:
                score += 22
            elif days_to_event >= 14:
                score += 18
            elif days_to_event >= 7:
                score += 12
            else:
                score += 6
        except:
            score += 15  # Default
    
    # Weather readiness (0-25)
    weather_badge = card.get("weather_badge")
    if weather_badge == "good":
        score += 25
    elif weather_badge == "mixed":
        score += 15
    elif weather_badge == "poor":
        score += 5
    else:
        score += 20  # Indoor or unknown
    
    # Financial readiness (0-25)
    cost = card.get("cost", 0)
    if cost > 0 and cash > 0:
        coverage_ratio = cash / cost
        if coverage_ratio >= 5:
            score += 25
        elif coverage_ratio >= 3:
            score += 22
        elif coverage_ratio >= 2:
            score += 18
        elif coverage_ratio >= 1:
            score += 10
        else:
            score += 5
    else:
        score += 15  # Default
    
    # Operational readiness (0-25) - simplified
    score += 20  # Default good operational readiness
    
    return min(score, 100)


def _format_date_range(start: Optional[str], end: Optional[str]) -> str:
    """Format date range for display (e.g., 'July 10-18')"""
    if not start:
        return ""
    
    try:
        from datetime import datetime
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        
        if end and end != start:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            if start_dt.month == end_dt.month:
                return f"{start_dt.strftime('%B')} {start_dt.day}-{end_dt.day}"
            else:
                return f"{start_dt.strftime('%b %d')} - {end_dt.strftime('%b %d')}"
        else:
            return start_dt.strftime("%B %d")
    except:
        return start


def _format_tracked_opportunities(tracked_opps: List[Dict]) -> List[Dict[str, Any]]:
    """Format tracked opportunities for table"""
    result = []
    for opp in tracked_opps:
        result.append({
            "id": str(opp.get("_id")),
            "opportunity": opp.get("title", ""),
            "category": opp.get("type", "Event"),
            "status": opp.get("status", "Tracked"),
            "deadline_date": opp.get("deadline", ""),
            "expected_roi": opp.get("expected_roi")
        })
    return result


def _calculate_historical_roi(outcomes: List[Dict]) -> Dict[str, Any]:
    """Calculate historical ROI from actual outcomes - returns null if no data"""
    if not outcomes:
        return {"multiplier": None, "sample_size": 0}
    
    roi_values = []
    for outcome in outcomes:
        revenue = outcome.get("actual_revenue", 0)
        cost = outcome.get("actual_cost", 0)
        if cost > 0 and revenue > 0:  # Only include valid outcomes
            roi = revenue / cost
            roi_values.append(roi)
    
    if roi_values:
        avg_roi = sum(roi_values) / len(roi_values)
        return {
            "multiplier": round(avg_roi, 1),
            "sample_size": len(roi_values)
        }
    
    # No valid outcomes - return null
    return {"multiplier": None, "sample_size": 0}
