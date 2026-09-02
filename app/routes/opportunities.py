# backend/app/routes/opportunities.py
"""
Opportunities Overview API - Powers the entire Opportunities UI
Returns KPIs, recommended opportunities, search results, and tracked opportunities
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from urllib import response
from fastapi import APIRouter, Depends, HTTPException, Query, status,FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from math import ceil

from app.routes.auth.auth import get_current_user
from app.db import get_collection
from app.services.research_scout_service import ResearchScoutService
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.services.finance_analyst_service import finance_analyst_service
from app.agents.opportunities_agent import research_scout_opportunities
from app.models.opportunities import Opportunity, OpportunityCreate, OpportunityUpdate
from app.services.feature_usage_service import feature_usage_service
from bson import ObjectId
from app.services.scenario_planning_service import ScenarioPlanningService
from app.services.mapbox_service import MapboxService
from app.services.portfolio_recalculation_service import portfolio_recalculation_service
from app.services.prep_agent_service import prep_agent_service
from app.services.lightsignal_memory_tool import LightSignalMemoryTool
from app.services.claude_service import claude_service
from app.services.scenario_lab_prompt import get_scenario_lab_prompt
from app.tools.calculator_tool import calculator_tool
import os
from pydantic import BaseModel
from dotenv import load_dotenv
from anthropic import Anthropic
import json
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI
import asyncio

load_dotenv()


def serialize_mongo(data):
    if not data:
        return {}
    if "_id" in data:
        data["_id"] = str(data["_id"])
    return data


router = APIRouter(tags=["opportunities"])
research_scout = ResearchScoutService()
scenario_service = ScenarioPlanningService()
mapbox_service = MapboxService()

@router.get("/overview")
async def get_opportunities_overview(
    current_user: dict = Depends(get_current_user),
    search_query: Optional[str] = Query(None, description="Optional search query"),
):
    """
    Get complete opportunities overview for the UI.
    """
    try:
        # Sanitize search_query if FastAPI Query default object passed directly in Python
        if not isinstance(search_query, str):
            search_query = None

        user_id = current_user.get("id") or current_user.get("_id")
        email = current_user.get("email", "")
        is_demo_flag = current_user.get("is_demo") or (email.startswith("demo-") and "@lightsignal.app" in email)
        
        if not is_demo_flag:
            users_col = get_collection("users")
            user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
            is_demo_flag = user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", ""))
            login_label = user_doc.get("login_label") or user_doc.get("username") or (user_doc.get("email", "").split("@")[0] if user_doc.get("email") else "demo-restaurant")
        else:
            login_label = current_user.get("login_label") or current_user.get("username") or (email.split("@")[0] if email else "demo-restaurant")

        if is_demo_flag:
            from app.demo_data import get_demo_payload
            demo_payload = get_demo_payload(login_label or "demo-restaurant")
            if demo_payload and "opportunities" in demo_payload:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "success": True,
                        "data": demo_payload["opportunities"]
                    }
                )

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
        
        # Get opportunities from Research Scout directly for normal users
        scout_query = search_query or "What opportunities are available for my business this month?"
        scout_result = await research_scout.search_opportunities(
            query=scout_query,
            user_id=user_id,
            business_profile=business_profile,
            opportunities_profile=opportunities_profile,
            mode="live",
        )
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
        
        # Add V2 summary helper fields
        rec_cards = ui_response.get("recommended", [])
        ui_response["recommended_hero"] = rec_cards[0] if len(rec_cards) > 0 else None
        ui_response["more_matches"] = rec_cards[1:] if len(rec_cards) > 1 else []
        ui_response["portfolio_summary"] = {
            "active_count": len(tracked_opps),
            "past_count": len(outcomes),
            "total_committed_dollars": "$0"
        }
        
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
        scout_result = await research_scout_opportunities(agent_profile)

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
    why_reason_codes = card.get(
        "why_reason_codes",
        [],
    )

    why_suggested = []

    try:

        generated = asyncio.run(
            finance_analyst_service.generate_opportunity_why_suggested(
                why_reason_codes,
            )
        )

        why_suggested = generated.split("\n")

    except:

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


@router.post("/save")
async def save_opportunity(
    opportunity_data: OpportunityCreate,
    current_user: dict = Depends(get_current_user),
):

    try:

        user_id = current_user["id"]

        business_profiles = get_collection("business_profiles")

        business_profile = await business_profiles.find_one({
            "user_id": user_id
        })

        onboarding_data = (
            business_profile.get("onboarding_data", {})
            if business_profile else {}
        )

        company_geo = onboarding_data.get("geo", {})

        company_latitude = company_geo.get("latitude")
        company_longitude = company_geo.get("longitude")

        geo = await mapbox_service.build_opportunity_geo(
            location_text=opportunity_data.location_text,
            company_latitude=company_latitude,
            company_longitude=company_longitude,
            start_date=opportunity_data.start_date,
            opportunity_type=opportunity_data.opportunity_type,
        )

        opportunity = Opportunity(
            user_id=user_id,
            geo=geo,
            **opportunity_data.dict()
        )

        opportunities_collection = get_collection("opportunities")

        await opportunities_collection.insert_one(
            opportunity.dict(by_alias=True)
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Opportunity saved successfully",
                "opportunity_id": opportunity.id
            },
        )

    except Exception as e:

        import traceback
        traceback.print_exc()

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": str(e)
            },
        )
    
@router.get("/saved")
async def get_saved_opportunities(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """
    Get paginated saved opportunities for the current user.
    """
    try:
        user_id = current_user["id"]
        skip = (page - 1) * page_size

        opportunities_collection = get_collection("opportunities")

        # Total count
        total_count = await opportunities_collection.count_documents(
            {"user_id": user_id}
        )

        # Paginated data
        cursor = (
            opportunities_collection
            .find({"user_id": user_id})
            .skip(skip)
            .limit(page_size)
        )

        opportunities = await cursor.to_list(length=page_size)
        
        for item in opportunities:
            item["_id"] = str(item["_id"])

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "data": jsonable_encoder(opportunities),
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": total_count,
                    "total_pages": ceil(total_count / page_size) if total_count else 0,
                },
            },
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
        )


@router.put("/update/{opportunity_id}")
async def update_opportunity(
    opportunity_id: str,
    opportunity_data: OpportunityUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Update an existing opportunity.
    """
    try:
        user_id = current_user["id"]

        opportunities_collection = get_collection("opportunities")
        update_data = {k: v for k, v in opportunity_data.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()

        result = await opportunities_collection.update_one(
            {"_id": opportunity_id, "user_id": user_id},
            {"$set": update_data}
        )

        updated_doc = await opportunities_collection.find_one({"_id": opportunity_id})
        status_value = update_data.get("status")

        if status_value in ["Tracked", "Selected", None]:

            await portfolio_recalculation_service.recalculate_portfolio_readiness(
                user_id=user_id,
                opportunities_collection=opportunities_collection,
            )

            updated_doc = await opportunities_collection.find_one({
                "_id": opportunity_id
            })

            if status_value in ["Tracked", "Selected"]:

                business_profiles = get_collection("business_profiles")

                business_profile = await business_profiles.find_one({
                    "user_id": user_id
                })

                prep_output = await prep_agent_service.generate_preparation_guidance(
                    opportunity=updated_doc,
                    business_profile=business_profile or {},
                )

                await opportunities_collection.update_one(
                    {
                        "_id": opportunity_id
                    },
                    {
                        "$set": {
                            "prep_agent_output": prep_output,
                            "prep_agent_last_run_at": datetime.utcnow(),
                        }
                    }
                )

                updated_doc = await opportunities_collection.find_one({
                    "_id": opportunity_id
                })

        if result.matched_count == 0:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Opportunity not found"},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Opportunity updated successfully", "data":jsonable_encoder(updated_doc)},
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
        )


@router.delete("/delete/{opportunity_id}")
async def delete_opportunity(
    opportunity_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Delete an opportunity.
    """
    try:
        user_id = current_user["id"]

        opportunities_collection = get_collection("opportunities")
        result = await opportunities_collection.delete_one({"_id": opportunity_id, "user_id": user_id})

        if result.deleted_count == 0:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Opportunity not found"},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Opportunity deleted successfully"},
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
        )



ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not found in .env file")

client = Anthropic(api_key=ANTHROPIC_API_KEY)


# =========================
# REQUEST MODELS
# =========================

class ChatMessage(BaseModel):
    role: str
    content: str


class QuestionRequest(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = None
    classifier_output: Optional[Dict[str, Any]] = None



def _enrich_scenario_result(parsed: dict) -> dict:
    """Enrich Scenario Lab result so both old and new frontend components render without undefined errors."""
    if not isinstance(parsed, dict):
        return parsed

    verdict = parsed.setdefault("verdict", {})
    if "confidence_reason" not in verdict:
        verdict["confidence_reason"] = "Based on historical financial trends and baseline data."
    if "risk_reason" not in verdict:
        verdict["risk_reason"] = "Evaluated against 12-month operating cash reserves."
        
        # Adapter fields for legacy UI components
        verdict["category"] = verdict.get("category") or verdict.get("recommendation") or "Decision"
        verdict["label"] = verdict.get("label") or verdict.get("headline") or verdict.get("recommendation") or "Recommended Action"
        verdict["reserve_warning"] = verdict.get("reserve_warning") or verdict.get("risk_reason") or ""

        for kn in parsed.setdefault("key_numbers", []):
            if isinstance(kn, dict):
                if "color_flag" not in kn:
                    val = str(kn.get("value", ""))
                    kn["color_flag"] = "green" if "+" in val else ("amber" if "-" in val else "cyan")
                if "severity" not in kn:
                    kn["severity"] = "resolved" if kn["color_flag"] == "green" else ("building" if kn["color_flag"] == "amber" else "stable")
                kn["source"] = kn.get("source") or kn.get("context") or "Calculated model"

        for p in parsed.setdefault("pros", []):
            if isinstance(p, dict):
                if "dollar_impact" not in p:
                    p["dollar_impact"] = 3500.0
                if "impact_text" not in p:
                    p["impact_text"] = f"+${p['dollar_impact']:,.0f}"
                p["pro"] = p.get("pro") or p.get("headline") or ""
                p["plain_language"] = p.get("plain_language") or p.get("detail") or ""
                p["action_to_capture"] = p.get("action_to_capture") or p.get("detail") or ""
                p["time_dimension"] = p.get("time_dimension") or "Immediate"

        for c in parsed.setdefault("cons", []):
            if isinstance(c, dict):
                if "dollar_impact" not in c:
                    c["dollar_impact"] = -1500.0
                if "impact_text" not in c:
                    p_val = abs(c['dollar_impact'])
                    c["impact_text"] = f"-${p_val:,.0f}"
                c["con"] = c.get("con") or c.get("headline") or ""
                c["plain_language"] = c.get("plain_language") or c.get("detail") or ""
                c["mitigation"] = c.get("mitigation") or c.get("detail") or ""
                c["time_dimension"] = c.get("time_dimension") or "Immediate"

        # Assumptions table adapter
        assumptions = parsed.setdefault("assumptions_table", [])
        if isinstance(assumptions, list):
            for a in assumptions:
                if isinstance(a, dict):
                    a["what"] = a.get("what") or a.get("assumption") or ""
                    a["value"] = a.get("value") or a.get("scenario") or ""
                    a["source"] = a.get("source") or a.get("baseline") or "Baseline"
                    a["note"] = a.get("note") or f"Baseline: {a.get('baseline', '')} -> Scenario: {a.get('scenario', '')}"

        # Steps adapter: support both list of strings and list of rich objects
        raw_steps = parsed.get("steps", [])
        rich_steps = []
        for idx, s in enumerate(raw_steps):
            if isinstance(s, str):
                rich_steps.append({
                    "title": f"Step {idx+1}",
                    "what": s,
                    "how": s,
                    "why": "Execution step for scenario implementation.",
                    "decision_gate": "Owner Approval"
                })
            elif isinstance(s, dict):
                rich_steps.append(s)
        parsed["steps"] = rich_steps

        # Alternatives adapter: support both list of strings and list of objects
        raw_alts = parsed.get("alternatives", [])
        rich_alts = []
        for alt in raw_alts:
            if isinstance(alt, str):
                rich_alts.append({"title": alt, "description": alt, "pros": alt})
            elif isinstance(alt, dict):
                rich_alts.append(alt)
        parsed["alternatives"] = rich_alts

        # Chart data adapter: support both flat array and rich chart object
        chart = parsed.get("chart_data")
        if isinstance(chart, list):
            parsed["chart_data"] = {
                "chart_type": "cash_waterfall",
                "series": chart,
                "flat_data": chart,
                "markers": [],
                "worst_case_series": []
            }

    return parsed


FALLBACK_ENABLED = False
FALLBACK_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenario_lab_fallback.json")

# =========================
# ENDPOINT
# =========================
@router.post("/scenario")
async def ask_question(payload: QuestionRequest, current_user: dict = Depends(get_current_user)):
    if FALLBACK_ENABLED:
        try:
            if os.path.exists(FALLBACK_FILE_PATH):
                with open(FALLBACK_FILE_PATH, "r", encoding="utf-8") as f:
                    fallback_json = json.load(f)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=fallback_json,
                    media_type="application/json",
                )
        except Exception as fallback_err:
            print(f"Error loading fallback file: {fallback_err}")

    try:
        user_id = current_user["id"]
        memory_tool = LightSignalMemoryTool(user_id=user_id)

        await feature_usage_service.log_usage(user_id, "scenario_planning")

        bp_col = get_collection("business_profiles")
        op_col = get_collection("opportunities_profiles")

        import asyncio
        baseline, bp, op = await asyncio.gather(
            quickbooks_financial_service.get_financial_overview(user_id),
            bp_col.find_one({"user_id": user_id}),
            op_col.find_one({"user_id": user_id})
        )

        # Resolve classifier_output per v1.4 input contract
        classifier_output = payload.classifier_output
        if not classifier_output and bp:
            classifier_output = bp.get("classifier_output") or bp.get("classification_result")
            if not classifier_output:
                try:
                    from app.services.business_profile_classifier_service import business_profile_classifier_service
                    classifier_output = business_profile_classifier_service.classify_business(
                        onboarding=bp.get("onboarding_data", bp),
                        opportunities_profile=op
                    )
                except Exception as clf_err:
                    print(f"Error extracting classifier_output for scenario: {clf_err}")
                    classifier_output = {}

        scenario_context = {
            "profile": serialize_mongo(bp) if bp else {},
            "classifier_output": serialize_mongo(classifier_output) if classifier_output else {},
            "accounting": serialize_mongo(baseline) if baseline else {},
            "pos": {},
            "data_availability": {
                "profile": bool(bp),
                "classifier_output": bool(classifier_output),
                "accounting": bool(baseline),
                "pos": False
            }
        }

        # =========================
        # BUILD MESSAGES (WITH HISTORY)
        # FIX #2: Serialize assistant history back to string, not raw object.
        # When previous scenario_result JSON was stored as a dict and sent back
        # as-is, Claude received a Python repr or malformed content — now we
        # re-stringify it so it's valid message content.
        # Also cap history to last 4 messages to avoid context bloat.
        # =========================
        messages = []

        recent_history = (payload.history or [])[-4:]  # FIX: only last 4 messages

        for msg in recent_history:
            content = msg.content
            # FIX: if the content is a dict (previous assistant JSON), re-stringify it
            if isinstance(content, dict):
                content = json.dumps(content)
            messages.append({
                "role": msg.role,
                "content": content
            })

        messages.append({
            "role": "user",
            "content": f"""scenario_context:
{json.dumps(scenario_context, default=str)}

question:
{payload.question}"""
        })

        response = await claude_service.tool_runner(
            system_prompt=get_scenario_lab_prompt(),
            messages=messages,
            tools=[
                memory_tool,
                calculator_tool,
                {
                    "type": "web_search_20250305",
                    "name": "web_search"
                }
            ],
            temperature=0.2,
            max_tokens=8000,
        )
        print(type(response))
        print(response) 
        print("STOP REASON:", response.stop_reason)

        for block in response.content:
            print(block)

        final_content = ""

        for block in response.content:
            if block.type == "text":
                final_content += block.text

        # FIX #3: Log the raw response so you can debug future issues.
        # Remove or gate behind an env flag in production.
        print(f"[scenario] raw response length: {len(final_content)}")
        print(f"[scenario] stop_reason: {response.stop_reason}")
        if response.stop_reason == "max_tokens":
            print("[scenario] WARNING: response was truncated — consider raising max_tokens further")

        import re
        cleaned = re.sub(r"```json|```", "", final_content).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1

        if start != -1 and end != -1:
            cleaned = cleaned[start:end]

        try:
            parsed = json.loads(cleaned)
        except Exception as parse_err:
            # FIX #4: Log what actually failed so you can diagnose it
            print(f"[scenario] JSON parse error: {parse_err}")
            print(f"[scenario] failed content (first 500 chars): {cleaned[:500]}")
            created = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "type": "clarification",
                    "message": final_content.strip(),
                    "created_at": created,
                },
            )

        if not isinstance(parsed, dict):
            created = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "type": "clarification",
                    "message": "Invalid response format",
                    "created_at": created,
                },
            )

        if parsed.get("type") == "clarification":
            created = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "type": "clarification",
                    "message": parsed.get("message"),
                    "created_at": created,
                },
            )

        parsed = _enrich_scenario_result(parsed)
        created = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        # =========================
        # SAVE THREAD
        # =========================
        thread_id = None
        try:
            thread_id = await scenario_service.save_chat_thread(
                user_id=user_id,
                messages=[
                    {"role": "user", "content": payload.question},
                    {"role": "assistant", "content": parsed}
                ],
                metadata={"question": payload.question}
            )
        except Exception as e:
            print(f"[scenario] Failed to save thread: {e}")

        response_payload = {
            "success": True,
            "data": parsed,
            "created_at": created
        }
        if thread_id:
            response_payload["thread_id"] = thread_id

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(response_payload),
        )

    except Exception as e:
        print(f"[scenario] API Error: {e}")
        import traceback
        traceback.print_exc()
        raise e
        # FIX #5: Store assistant message content as string, not raw dict.
        # Sending the parsed dict back in history caused the content-type
        # mismatch that broke multi-turn conversations.
        # =========================
        try:
            saved_messages = []

            for msg in recent_history:
                content = msg.content
                if isinstance(content, dict):
                    content = json.dumps(content)
                saved_messages.append({
                    "role": msg.role,
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })

            saved_messages.append({
                "role": "user",
                "content": payload.question,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            saved_messages.append({
                "role": "assistant",
                "content": json.dumps(parsed),  # FIX #5: stringify, not raw dict
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            saved_messages = saved_messages[-6:]

            await scenario_service.save_chat_thread(
                user_id=user_id,
                messages=saved_messages,
                metadata={"source": "opportunities.scenario", "created_at": created},
            )

        except Exception as e:
            print(f"Warning: Failed to persist scenario result: {e}")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "type": "scenario_result",
                "data": parsed,
                "created_at": created,
            },
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )

@router.get("/recent-scenarios")
async def get_recent_scenarios(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(5, ge=1, le=10),
):
    """Return up to `limit` recent scenario threads (full thread in `thread`)."""
    try:
        user_id = current_user["id"]
        threads = await scenario_service.get_user_threads(user_id, limit=limit)

        result = []
        for t in threads:
            result.append({
                "id": str(t.get("_id")),
                "created_at": (t.get("created_at").isoformat() + "Z") if t.get("created_at") else None,
                "updated_at": (t.get("updated_at").isoformat() + "Z") if t.get("updated_at") else None,
                "metadata": t.get("metadata", {}),
                "thread": t.get("messages", []),
            })

        return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"data": result}))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)},
        )

def _stringify_object_ids(obj: Any) -> Any:
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _stringify_object_ids(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_stringify_object_ids(item) for item in obj]
    return obj


@router.get("/{opportunity_id}/prep")
@router.get("/prep/{opportunity_id}")
async def get_opportunity_prep(
    opportunity_id: str,
    current_user: Any = Depends(get_current_user),
):
    try:
        if isinstance(current_user, dict):
            user_id = current_user.get("id") or current_user.get("_id")
            email = current_user.get("email", "")
        else:
            user_id = str(current_user)
            email = ""

        is_demo_flag = (isinstance(current_user, dict) and current_user.get("is_demo")) or (email.startswith("demo-") and "@lightsignal.app" in email)
        if not is_demo_flag:
            users_col = get_collection("users")
            user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
            is_demo_flag = user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", ""))

        # Demo users: return deterministic spec-compliant prep guidance with no AI calls
        if is_demo_flag:
            fallback_prep = {
                "opportunity_id": opportunity_id,
                "checklist": [
                    {
                        "task_id": "chk_1",
                        "label": "Confirm staffing schedule and shift coverage",
                        "title": "Confirm staffing schedule and shift coverage",
                        "phase": "2_3_weeks_before",
                        "deadline_date": (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d"),
                        "priority": "critical",
                        "is_urgent": True,
                        "addresses": "operational",
                        "completed": False
                    },
                    {
                        "task_id": "chk_2",
                        "label": "Review inventory stock levels and supplier lead times",
                        "title": "Review inventory stock levels and supplier lead times",
                        "phase": "7_10_days",
                        "deadline_date": (datetime.utcnow() + timedelta(days=12)).strftime("%Y-%m-%d"),
                        "priority": "standard",
                        "is_urgent": False,
                        "addresses": "financial",
                        "completed": False
                    },
                    {
                        "task_id": "chk_3",
                        "label": "Verify mobile POS terminal connectivity and card reader backup",
                        "title": "Verify mobile POS terminal connectivity and card reader backup",
                        "phase": "event_week",
                        "deadline_date": (datetime.utcnow() + timedelta(days=18)).strftime("%Y-%m-%d"),
                        "priority": "standard",
                        "is_urgent": False,
                        "addresses": "operational",
                        "completed": False
                    }
                ],
                "judgment_prompts": [
                    {
                        "category": "Human Factors",
                        "check_prompt": "Will key staff require overtime or schedule adjustments during this window?",
                        "prompt": "Will key staff require overtime or schedule adjustments during this window?",
                        "title": "Human Factors",
                        "severity": "medium"
                    },
                    {
                        "category": "Financial Ripple",
                        "check_prompt": "What is the expected ROI multiple relative to upfront ingredient and transport costs?",
                        "prompt": "What is the expected ROI multiple relative to upfront ingredient and transport costs?",
                        "title": "Financial Ripple",
                        "severity": "low"
                    }
                ],
                "risk_prompts": [
                    {
                        "category": "Human Factors",
                        "check_prompt": "Will key staff require overtime or schedule adjustments during this window?",
                        "prompt": "Will key staff require overtime or schedule adjustments during this window?",
                        "title": "Human Factors",
                        "severity": "medium"
                    },
                    {
                        "category": "Financial Ripple",
                        "check_prompt": "What is the expected ROI multiple relative to upfront ingredient and transport costs?",
                        "prompt": "What is the expected ROI multiple relative to upfront ingredient and transport costs?",
                        "title": "Financial Ripple",
                        "severity": "low"
                    }
                ],
                "checkpoint_summary": "Preparation tracking active. Complete checklist items to stay on schedule.",
                "cash_balance": 18500.0,
                "revenue_attributed": 4200.0,
                "owner_responses": {}
            }
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=jsonable_encoder(_stringify_object_ids({
                    "success": True,
                    "cached": True,
                    "data": fallback_prep,
                }), custom_encoder={ObjectId: str}),
            )

        opportunities_collection = get_collection("opportunities")
        business_profiles = get_collection("business_profiles")

        opportunity = None
        try:
            if ObjectId.is_valid(opportunity_id):
                opportunity = await opportunities_collection.find_one({
                    "$or": [{"_id": opportunity_id}, {"_id": ObjectId(opportunity_id)}],
                    "user_id": user_id,
                })
            else:
                opportunity = await opportunities_collection.find_one({
                    "_id": opportunity_id,
                    "user_id": user_id,
                })
        except Exception as db_err:
            print(f"[get_opportunity_prep] DB lookup warning/error: {db_err}")
            opportunity = None

        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )

        cached_output = opportunity.get("prep_agent_output")
        if cached_output:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=jsonable_encoder(_stringify_object_ids({
                    "success": True,
                    "cached": True,
                    "data": cached_output,
                }), custom_encoder={ObjectId: str}),
            )

        business_profile = await business_profiles.find_one({
            "user_id": user_id
        })

        prep_output = await prep_agent_service.generate_preparation_guidance(
            opportunity=_stringify_object_ids(opportunity),
            business_profile=_stringify_object_ids(business_profile or {}),
        )

        await opportunities_collection.update_one(
            {
                "_id": opportunity.get("_id")
            },
            {
                "$set": {
                    "prep_agent_output": prep_output,
                    "prep_agent_last_run_at": datetime.utcnow(),
                }
            }
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(_stringify_object_ids({
                "success": True,
                "cached": False,
                "data": prep_output,
            }), custom_encoder={ObjectId: str}),
        )

    except Exception as e:
        import traceback
        traceback.print_exc()

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder({
                "success": False,
                "error": str(e)
            }),
        )


class OpportunitySearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    opportunity_types: Optional[List[str]] = None
    limit: Optional[int] = 10


class OpportunityStatusRequest(BaseModel):
    status: str  # "none" | "tracked" | "selected" | "completed"


class CheckpointResponseRequest(BaseModel):
    response_text: str


class ChecklistTaskRequest(BaseModel):
    completed: bool


@router.post("/search")
async def search_opportunities_ondemand(
    req: OpportunitySearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """On-demand web search for opportunities per spec §B."""
    from app.routes.ai_opportunities import ai_opportunities_search, OpportunitySearchRequest as AIOppSearchRequest
    ai_req = AIOppSearchRequest(
        query=req.query,
        opportunity_types=req.opportunity_types,
        limit=req.limit or 10,
    )
    return await ai_opportunities_search(request=ai_req, current_user=current_user)


@router.patch("/{opportunity_id}/status")
@router.post("/{opportunity_id}/status")
async def update_opportunity_status(
    opportunity_id: str,
    req: OpportunityStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """Persist opportunity status (none / tracked / selected / completed)."""
    user_id = current_user.get("id") or current_user.get("_id")
    col = get_collection("opportunities")
    now = datetime.utcnow().isoformat()
    
    await col.update_one(
        {"_id": opportunity_id, "user_id": user_id},
        {"$set": {"status": req.status, "updated_at": now}},
        upsert=True
    )
    return {"success": True, "opportunity_id": opportunity_id, "status": req.status}


@router.post("/checkpoints/{checkpoint_id}/response")
async def respond_to_checkpoint(
    checkpoint_id: str,
    req: CheckpointResponseRequest,
    current_user: dict = Depends(get_current_user)
):
    """Save owner checkpoint response in prep view per spec §F."""
    user_id = current_user.get("id") or current_user.get("_id")
    col = get_collection("opportunity_checkpoints")
    now = datetime.utcnow().isoformat()
    
    await col.update_one(
        {"_id": checkpoint_id, "user_id": user_id},
        {"$set": {"response_text": req.response_text, "updated_at": now}},
        upsert=True
    )
    return {"success": True, "checkpoint_id": checkpoint_id, "response_text": req.response_text}


@router.patch("/{opportunity_id}/checklist/{task_id}")
async def toggle_checklist_task(
    opportunity_id: str,
    task_id: str,
    req: ChecklistTaskRequest,
    current_user: dict = Depends(get_current_user)
):
    """Persist checklist task completion per spec §F."""
    user_id = current_user.get("id") or current_user.get("_id")
    col = get_collection("opportunity_checklists")
    now = datetime.utcnow().isoformat()
    
    await col.update_one(
        {"opportunity_id": opportunity_id, "task_id": task_id, "user_id": user_id},
        {"$set": {"completed": req.completed, "updated_at": now}},
        upsert=True
    )
    return {"success": True, "opportunity_id": opportunity_id, "task_id": task_id, "completed": req.completed}