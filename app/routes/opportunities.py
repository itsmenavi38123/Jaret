# backend/app/routes/opportunities.py
"""
Opportunities Overview API - Powers the entire Opportunities UI
Returns KPIs, recommended opportunities, search results, and tracked opportunities
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
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

import os
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI
import json
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI

load_dotenv()


router = APIRouter(tags=["opportunities"])
research_scout = ResearchScoutService()
scenario_service = ScenarioPlanningService()


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


@router.post("/save")
async def save_opportunity(
    opportunity_data: OpportunityCreate,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]

    opportunity = Opportunity(
        user_id=user_id,
        **opportunity_data.dict()
    )

    opportunities_collection = get_collection("opportunities")
    result = await opportunities_collection.insert_one(opportunity.dict(by_alias=True))

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Opportunity saved successfully",
            "opportunity_id": opportunity.id
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



OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found")

client_async = AsyncOpenAI(api_key=OPENAI_API_KEY)


# =========================
# REQUEST MODELS
# =========================

class ChatMessage(BaseModel):
    role: str
    content: str


class QuestionRequest(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = []


# =========================
# SYSTEM PROMPT (STRUCTURED)
# =========================

SYSTEM_PROMPT = """
    You are the LightSignal Scenario Planning Lab.

    You are a conversational, agent-driven decision partner for small business owners.

    You operate in TWO MODES ONLY.

    ========================================
    MODE 1: CLARIFICATION
    ========================================

    If you need additional information before running financial analysis,
    you MUST return EXACTLY this JSON structure:

    {
    "type": "clarification",
    "message": "Your clarification question here"
    }

    Rules:
    - Ask maximum 3 clarification questions.
    - Ask only high-value questions that materially change financial results.
    - Do NOT include any additional text outside JSON.
    - Do NOT include explanations outside the JSON.
    - Do NOT use markdown.

    ========================================
    MODE 2: SCENARIO RESULT
    ========================================

    When you have enough information, you MUST return ONE JSON object
    with EXACTLY the following structure.

    Do NOT include any text outside this JSON.

    {
    "type": "scenario_result",

    "headline": "Short executive summary sentence (clear, calm, decision-oriented).",

    "confidence": {
        "score": 0,
        "label": "High | Moderate | Low",
        "explanation": "Short explanation of why this confidence level."
    },

    "risk": {
        "level": "High | Medium | Low",
        "score": 0,
        "factors": [
        "Risk factor 1",
        "Risk factor 2"
        ]
    },

    "impact_cards": [
        {
        "id": "card_1",
        "label": "Card Title",
        "value": "Formatted Value",
        "format": "currency | range_percentage | range_months | months_range | category | range_currency",
        "severity": "high | medium | low",
        "details": {
            "best": 0,
            "expected": 0,
            "worst": 0,
            "baseline_value": 0,
            "explanation": "Explanation of calculation"
        }
        },
        {
        "id": "card_2",
        "label": "Card Title",
        "value": "Formatted Value",
        "format": "currency | range_percentage | range_months | months_range | category | range_currency",
        "severity": "high | medium | low",
        "details": {
            "best": 0,
            "expected": 0,
            "worst": 0,
            "baseline_value": 0,
            "explanation": "Explanation of calculation"
        }
        },
        {
        "id": "card_3",
        "label": "Card Title",
        "value": "Formatted Value",
        "format": "currency | range_percentage | range_months | months_range | category | range_currency",
        "severity": "high | medium | low",
        "details": {
            "best": 0,
            "expected": 0,
            "worst": 0,
            "baseline_value": 0,
            "explanation": "Explanation of calculation"
        }
        },
        {
        "id": "card_4",
        "label": "Card Title",
        "value": "Formatted Value",
        "format": "currency | range_percentage | range_months | months_range | category | range_currency",
        "severity": "high | medium | low",
        "details": {
            "best": 0,
            "expected": 0,
            "worst": 0,
            "baseline_value": 0,
            "explanation": "Explanation of calculation"
        }
        }
    ],

    "financial_sensitivity": {
        "type": "line",
        "title": "Financial Sensitivity (Best/Expected/Worst)",
        "x_axis": ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
        "series": {
        "best": [0,0,0,0,0,0],
        "expected": [0,0,0,0,0,0],
        "worst": [0,0,0,0,0,0]
        }
    },

    "demand_response_curve": {
        "type": "curve",
        "title": "Demand Response Curve",
        "data": [
        {"x": 0, "y": 100},
        {"x": 20, "y": 90},
        {"x": 40, "y": 75},
        {"x": 60, "y": 60},
        {"x": 80, "y": 50},
        {"x": 100, "y": 40}
        ]
    },

    "strategic_steps": [
        {
        "title_1": "Step Title",
        "bullets": [
            "Action 1",
            "Action 2",
            "Action 3"
        ]
        },
        {
        "title_2": "Step Title",
        "bullets": [
            "Action 1",
            "Action 2",
            "Action 3"
        ]
        },
                {
        "title_3": "Step Title",
        "bullets": [
            "Action 1",
            "Action 2",
            "Action 3"
        ]
        },
                {
        "title_4": "Step Title",
        "bullets": [
            "Action 1",
            "Action 2",
            "Action 3"
        ]
        }
    ],

    "pros": [
        "Pro 1",
        "Pro 2",
        "Pro 3"
    ],

    "cons": [
        "Con 1",
        "Con 2",
        "Con 3"
    ],

    "things_to_keep_in_mind": [
        "Important consideration 1",
        "Important consideration 2"
    ],

    "peer_context": "Short paragraph explaining what similar businesses typically experience.",

    "cost_response_insight": "Short practical insight about cost and response tradeoffs.",

    "assumptions_table": [
        {
        "key": "assumption_name",
        "value": 0,
        "source": "user | accounting | profile | prior",
        "note": "Explanation of assumption"
        }
    ],

    "recommendation": {
        "decision": "Proceed | Proceed with caution | Delay | Do not proceed",
        "reasoning": "Clear explanation of recommended action.",
        "next_steps": [
        "Next step 1",
        "Next step 2",
        "Next step 3"
        ]
    }
    }

    ========================================
    STRICT RULES
    ========================================

    - NEVER return markdown.
    - NEVER return explanation outside JSON.
    - NEVER hallucinate numbers.
    - ALWAYS use tools for financial data.
    - ALWAYS return exactly 4 impact_cards.
    - ALWAYS include confidence, risk, charts, assumptions_table.
    - If scenario does not require demand_response_curve, return null.
    - Output must be valid JSON only.
    """

# =========================
# ENDPOINT
# =========================

@router.post("/scenario")
async def ask_question(payload: QuestionRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["id"]

        await feature_usage_service.log_usage(user_id, "scenario_planning")

        # Build conversation
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in payload.history:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": payload.question})

        # =========================
        # TOOL DEFINITIONS
        # =========================

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "fetchBaseline",
                    "description": "Fetch baseline financials from accounting",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {"type": "string"},
                            "periods": {"type": "integer"},
                            "scope": {"type": "string"}
                        },
                        "required": ["company_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetchProfile",
                    "description": "Fetch business profile",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {"type": "string"}
                        },
                        "required": ["company_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "getScenarioPriorsFromResearchScout",
                    "description": "Get market priors",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {"type": "string"},
                            "scenario_type": {"type": "string"},
                            "industry": {"type": "string"},
                            "region": {"type": "string"},
                            "assumption_slots": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["company_id", "scenario_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "runFinanceScenario",
                    "description": "Run Finance Analyst and return STRICT JSON",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scenario_type": {"type": "string"},
                            "baseline": {"type": "object"},
                            "assumptions": {"type": "object"},
                            "horizon_months": {"type": "integer"},
                            "location_scope": {"type": "string"},
                            "stress_cases": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["scenario_type", "baseline", "assumptions"]
                    }
                }
            }
        ]


        # =========================
        # TOOL EXECUTION HANDLER
        # =========================

        async def _execute_tool(function_name: str, args: dict):

            # Always inject company_id from auth
            args["company_id"] = user_id

            if function_name == "fetchBaseline":
                try:
                    return await quickbooks_financial_service.get_financial_overview(user_id)
                except Exception as e:
                    return {"error": str(e)}

            if function_name == "fetchProfile":
                try:
                    bp_col = get_collection("business_profiles")
                    op_col = get_collection("opportunities_profiles")
                    bp = await bp_col.find_one({"user_id": user_id})
                    op = await op_col.find_one({"user_id": user_id})
                    return {"business_profile": bp or {}, "opportunities_profile": op or {}}
                except Exception as e:
                    return {"error": str(e)}

            if function_name == "getScenarioPriorsFromResearchScout":
                try:
                    result = await research_scout.search_opportunities(
                        query=f"Priors for {args.get('scenario_type')}",
                        user_id=user_id,
                        business_profile=None,
                        opportunities_profile=None,
                        mode="live",
                    )
                    return result
                except Exception as e:
                    return {"error": str(e)}

            if function_name == "runFinanceScenario":
                try:
                    return await finance_analyst_service.calculate_scenario_kpis(
                        scenario_type=args.get("scenario_type"),
                        query=payload.question,
                        assumptions=args.get("assumptions"),
                        baseline_financials=args.get("baseline"),
                        business_profile=None,
                    )
                except Exception as e:
                    return {"error": str(e)}

            return {"error": f"Unknown tool {function_name}"}

        # =========================
        # TOOL CALL LOOP
        # =========================

        clarification_count = 0
        max_clarifications = 3

        response = await client_async.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
        )

        while True:
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)

            if not tool_calls:
                break

            messages.append(message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                tool_result = await _execute_tool(function_name, function_args)

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result, default=str),
                })

            response = await client_async.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.2,
            )

        # =========================
        # FINAL RESPONSE HANDLING
        # =========================

        final_content = response.choices[0].message.content

        try:
            parsed = json.loads(final_content)
        except Exception:
            # treat as clarification text
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

        # Clarification mode
        if parsed.get("type") == "clarification":
            clarification_count += 1
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

        # Scenario result mode
        created = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        # Persist scenario conversation/result (non-fatal)
        try:
            # Build saved thread from provided history (user/assistant pairs), then current question
            saved_messages = []
            # payload.history contains ChatMessage objects with role/content
            for msg in (payload.history or []):
                saved_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })

            # Append current user question
            saved_messages.append({
                "role": "user",
                "content": payload.question,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            # Append assistant final JSON response (store as JSON object)
            saved_messages.append({
                "role": "assistant",
                "content": parsed,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            # Keep at most the last 6 messages in the thread
            saved_messages = saved_messages[-6:]

            await scenario_service.save_chat_thread(
                user_id=user_id,
                messages=saved_messages,
                metadata={"source": "opportunities.scenario", "created_at": created},
            )
        except Exception as e:
            print(f"Failed to persist scenario result: {e}")

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


