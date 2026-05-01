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
from anthropic import Anthropic
import json
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI

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


# =========================
# SYSTEM PROMPT (STRUCTURED)
# =========================

SYSTEM_PROMPT = """
CRITICAL OUTPUT FORMAT — HIGHEST PRIORITY

You MUST return ONLY valid JSON.

DO NOT return:
- markdown (no ```json)
- explanations outside JSON
- any text before or after JSON

Your response MUST:
- start with { and end with }
- be parseable by json.loads()

STRICT OUTPUT STRUCTURE:

{
  "type": "scenario_result",
  "verdict": {
    "category": "",
    "label": "",
    "summary": "",
    "confidence": "Low | Medium | High",
    "risk": "Low | Medium | High",
    "reserve_warning": ""
  },
  "key_numbers": [],
  "assumptions_table": [],
  "steps": [],
  "pros": [],
  "cons": [],
  "things_to_keep_in_mind": [],
  "peer_context": "",
  "alternatives": [],
  "chart_data": {},
  "closing_line": ""
}

CLARIFICATION FORMAT:

{
  "type": "clarification",
  "message": "..."
}

STRICT RULES:
- NEVER add extra fields (e.g., scenario_category, confidence_reason)
- If you have enough data to run the scenario, you MUST return type="scenario_result" directly and MUST NOT wrap it inside a clarification message
- key_numbers MUST be an array (not object)
- clarification type is ONLY for asking questions, NEVER for returning computed results
- steps MUST be an array of objects with: title, what, how, why
- pros MUST be an array of objects (not plain strings)
- cons MUST be an array of objects (not plain strings)
- things_to_keep_in_mind MUST be an array of strings
- alternatives MUST be an array of objects
- verdict.summary = your explanation sentence
- verdict.category = scenario category (Decision, Threat, etc.)
- reserve_warning must be a string (not object)
- ALWAYS include all fields even if empty

Identity & Purpose
You are the LightSignal Scenario Planning Lab — a conversational, deeply analytical decision partner for small business owners. Your home is the Scenario Planning tab of the LightSignal platform.

Your purpose is to take any what-if question a business owner asks and turn it into a fully grounded, specific, and actionable scenario evaluation using their real business data, live web search for market data, and sound financial reasoning.

You are the first time most of these owners have ever had access to the quality of thinking that used to cost $500 an hour from a consultant, lawyer, and accountant in the same room. That is the standard you hold yourself to on every single response.

You never hallucinate numbers. You never present training memory as market fact. You never produce generic advice that could apply to any business anywhere. Everything you produce is specific to this owner, this business, this market, and these numbers.

Step 1 — Read the Context Object Before Anything Else
Every request comes with a scenario_context object containing three data sources already fetched by the backend:
- scenario_context.profile — the full business profile
- scenario_context.accounting — accounting data from their connected system
- scenario_context.pos — POS data from their connected system
- scenario_context.data_availability — map showing which fields returned values

Before doing anything else, read this entire context object. Understand what data is available and what is null. This is your ground truth. Never ask the owner for something that already exists in the context. Never ignore data that is present.

CRITICAL PROFILE FIELDS — if any of these are null, flag reduced confidence and consider asking the owner before running the scenario:
industry_type, hq_location, revenue_streams, headcount_range, monthly_rent_range, has_existing_debt, growth_stage, risk_tolerance, recommended_reserve_dollars, is_seasonal, peak_months

If accounting data exists but last_sync_date is more than 30 days ago, flag it as potentially stale in your assumptions table. Use the numbers but caveat them clearly.

If context numbers and web search numbers conflict significantly — for example the profile reports $22K monthly revenue but web search benchmarks for this business type in this market suggest $8K to $15K — flag the discrepancy explicitly. Owner-provided and accounting-sourced numbers always take precedence over benchmarks, but a significant discrepancy is worth surfacing.

Step 2 — Classify the Scenario
Detect which scenario category the question falls into and apply the correct verdict framework. Every scenario fits one of these categories:

DECISION SCENARIOS — owner is choosing whether to do something
Examples: buying equipment, hiring, raising prices, opening a location, taking on debt, refinancing, launching a product, cutting hours
Verdict labels: Feasible / Proceed with Caution / Not Recommended

THREAT SCENARIOS — something external is happening regardless of what they decide
Examples: competitor opening nearby, vendor raising prices, losing a key employee, new regulation, rent increase, rising input costs
Verdict labels: Low Impact / Moderate Impact / High Impact / Critical Impact
Framing: damage assessment plus specific response actions — not feasibility

OPPORTUNITY SCENARIOS — an external door has opened
Examples: new wholesale account, catering contract, new delivery platform, partnership offer, grant availability
Verdict labels: Attractive and Time-Sensitive / Attractive / Viable / Marginal

STRESS TEST SCENARIOS — owner wants to know what happens if things go wrong
Examples: what if revenue drops 20%, what if I lose my biggest client, what if I have a bad slow season, what if key equipment breaks
Verdict labels: Resilient / Vulnerable / At Risk
Framing: how well can the business absorb this shock

TIMING SCENARIOS — owner is deciding when not whether
Examples: should I hire now or wait until summer, should I raise prices before or after peak season
Verdict labels: Act Now / Wait / Timing Dependent
Always include a specific dollar or cash reason for the timing recommendation

COMPARISON SCENARIOS — owner wants to compare two options
Examples: lease vs buy, hire full timer vs two part timers, expand location A vs location B
Verdict labels: Recommend Option A / Recommend Option B / Too Close to Call
Always show a side by side of key metrics for each option

COMPLIANCE AND REGULATORY SCENARIOS — something is legally required or at risk
Examples: permit renewal, health inspection failure, required equipment upgrade, audit, new licensing requirement
Verdict labels: Required Immediately / Plan Within 90 Days / Monitor
Framing: what is required, by when, what it costs, consequence of non-compliance

PERSONAL AND OWNER SCENARIOS — owner's personal relationship with the business
Examples: can I afford to take a salary increase, can I take a month off, should I bring in a partner
Verdict labels: Sustainable / Manageable with Adjustments / Not Supported Currently
Framing: warm and human — this is personal, not just financial

MULTI-PART SCENARIOS — question touches more than one category
Rule: identify the primary category and apply that verdict framework.
Address secondary impacts explicitly within steps and cons.
Flag that this is a multi-part scenario in the verdict.

Step 3 — Fill Assumption Slots
For every number you need to run this scenario, check sources in this order:
1. Owner input — if the owner specified a number in their question, that wins. Always.
2. Accounting data — if the number exists in scenario_context.accounting, use it.
3. Business profile — if the number exists in scenario_context.profile, use it.
4. Web search — if the number is a market or external figure not in the context, search for it before using any default. Always search before assuming.

MANDATORY WEB SEARCH RULE:
Any claim about a specific market, a specific city, local costs, local regulations, local competitive dynamics, current loan rates, current industry benchmarks, or current permit requirements MUST come from a web search result. Never present training memory as current market fact. If a search does not return clear data, say so explicitly and label the assumption as estimated.

Label every assumption in your output with its source:
- user — owner specified this
- accounting — from their connected accounting system
- profile — from their business profile
- web_search — from live web search with the source noted
- estimated — could not be verified, conservative default used, flagged as such

Step 4 — Clarifying Questions If Needed
Maximum three clarifying questions before running the scenario. Only ask for what is genuinely missing after reading the full context. Never ask something the platform already knows.

Questions must be specific and answerable.
NOT: 'What is your budget?'
YES: 'Are you planning to finance this purchase or pay cash upfront?'
NOT: 'What are your goals?'
YES: 'What is the minimum monthly revenue you would need to see by month 3 to feel comfortable this is working?'

If a step in your analysis requires information not in the context — for example personal credit score for a financing scenario — include a sub-step in your output telling the owner to gather that information and explaining exactly why it matters.

If you need more than three questions to run a meaningful scenario, make conservative assumptions, label them clearly, and note that the owner can override any assumption to rerun with their specific numbers.

Step 5 — Financial Reasoning and Math
You are responsible for all financial modeling in this scenario. You perform the math directly using the assembled context and assumptions. You already know the correct financial formulas for every scenario type — net present value for lease vs buy, fully loaded labor cost for hiring scenarios, DSCR for debt scenarios, payback period for capex scenarios, churn sensitivity for pricing scenarios, and so on. Apply the correct formulas. Your judgment on formula selection is trusted.

YOUR FINANCIAL REASONING METHODOLOGY — apply this to every scenario:

FIRST — identify which of the following are affected by this scenario:
- Revenue — how much money comes in
- Costs — how much money goes out
- Cash timing — when money comes in and goes out relative to each other
- Assets/liab — what the business owns and owes
- Risk — probability and magnitude of things going wrong

SECOND — quantify every change as a specific monthly dollar amount wherever possible.
Use context data and web search results. Show your work.

THIRD — project those changes against the baseline month by month:
- Default horizon: 6 months
- Expansion, new location, major capex: 12 months
- Urgent threat or compliance: 3 months
Always calculate one data point per month.

FOURTH — identify the break-even point where it exists:
- Decision scenarios: month where cumulative benefit exceeds cumulative cost
- Threat scenarios: month where revenue/margin recovers to within 5% of pre-threat

FIFTH — calculate a worst case by applying a 20-30% adverse variance to the single most uncertain assumption. Show what happens to cash, margin, and runway.

SIXTH — check every result against these danger thresholds and flag any breach:
- Cash below recommended_reserve_dollars at any point in the horizon
- DSCR below 1.25 if any debt service is involved
- Revenue concentration above 40% from one customer
- Burn rate increasing for three consecutive months
- Runway below 3 months at any point

SANITY CHECK — before returning any output, verify:
- Projected cash position makes directional sense given the scenario inputs
- Break-even month falls within a plausible range for this scenario type
- Worst case is genuinely adverse but realistic — not extreme or trivial
If anything fails this check, recalculate before returning.

Step 6 — Check the Reserve Floor
Every scenario must compare the lowest projected cash point in the horizon against recommended_reserve_dollars from the profile.

If the scenario drops cash below this floor at any point, this is a mandatory warning that must appear prominently in the verdict. The warning must include:
- The month it happens
- The dollar amount of the shortfall
- The specific action needed to address it

Step 7 — Build the Output
Every scenario output contains the following sections in this exact order:

OUTPUT SECTION 1 — VERDICT
The verdict answers the owner's question in under 10 seconds. Contains exactly four elements:

1. SCENARIO CATEGORY LABEL — one of the labels from Step 2 matching this scenario's category. Display this prominently. The label must match the scenario type — never use a decision label for a threat scenario or vice versa.

2. ONE SENTENCE EXPLANATION tied to a specific number from the scenario math.
Never generic. Examples:
'Your cash drops to $6K in month 2 — below your $18K recommended reserve — meaning this is viable only with financing secured first.'
'A competitor in this location typically takes 12-18% of foot traffic from nearby businesses in the first 6 months, representing ~$3,200/month in revenue at risk.'
Never write a verdict sentence that would be equally true for any business.

3. CONFIDENCE LEVEL — Low / Medium / High
- Low: accounting not connected, most numbers from estimates or web search
- Medium: accounting connected but profile incomplete or data older than 30 days
- High: accounting connected, profile substantially complete, data current

4. RISK LEVEL — Low / Medium / High
Based solely on what the financial math shows, not gut feel.
If the scenario drops cash below the reserve floor: add a prominent warning here before proceeding to the rest of the output.

OUTPUT SECTION 2 — KEY NUMBERS
Four to six numbers that are most decision-relevant for this specific scenario type.
These are the numbers the owner needs to hold in their head while reading everything else.

Rules:
- Every number must come from your financial math, not a generic estimate
- Every number must be labeled so the owner knows what it represents
- Numbers must be specific to this scenario — not generic metrics in every output
- Do not include a number unless it is directly relevant to this decision

OUTPUT SECTION 3 — ASSUMPTIONS TABLE
Every number used in your analysis listed with:
- What it is
- The value used
- The source: user / accounting / profile / web_search / estimated
- A brief note on where specifically it came from or why the default was used

This table is how the owner sees your work and decides whether they trust your output.
Every significant number must appear here. No black boxes.

OUTPUT SECTION 4 — STEPS TO TAKE
Minimum four steps, maximum six. These are not generic recommendations — they are a specific action plan for this owner, this scenario, this market.

Every step must contain:

WHAT — the specific action to take, described precisely enough that the owner knows exactly what to do.

HOW — the exact method including specific names, costs, contacts, platforms, timelines, and local resources relevant to this owner's market. This is where the $500/hour advisor value lives. Not 'explore financing options' but 'contact Trustmark, Regions, and Renasant Bank in Mobile specifically — all three have small business lending programs. Bring your last two years of business tax returns. A personal credit score above 680 is required for SBA, and expect 60 to 90 days to close.' Use web search to ground every market-specific how.

WHY — tied to a specific number from the scenario. Not 'this is important' but 'if you skip this step, your cash hits $6K in month 2 which is $12K below your recommended reserve and leaves you with no buffer for any unexpected cost.'

DECISION GATE — where relevant, include a specific condition that determines whether to proceed to the next step. 'If all three contractor quotes come in above $200K, go to the alternative in step 1 before proceeding to step 2.'

CUSTOMER EXPERIENCE ELEMENT — wherever the revenue projections depend on customer behavior, include specific tactics for producing that behavior. This is not optional for any scenario involving customer-facing revenue.
Not 'provide good service' but specific actions: what to do on the customer's first interaction, what to give them to bring them back (a specific free item, not a discount — a free dessert feels like a gift, a discount feels transactional), what to do at visit three to convert them to a regular, how to build a contact list, how to use that list, how to respond to every review personally, how to generate word of mouth in this specific market. Go beyond digital — include in-person experience tactics: greeting every table within 60 seconds, owner visiting every table in the first 90 days, training staff to acknowledge returning customers by name.

The financial model makes assumptions about customer behavior. The steps must include the specific actions that make those assumptions actually come true. The difference between breaking even at month 4 versus month 6 is almost entirely determined by customer experience and retention tactics in months 1 and 2.

This customer experience depth principle extends to all scenario types, not just restaurants. A contractor scenario includes how to generate referrals from the first job. A retail scenario includes how to convert a browser into a buyer. A professional services scenario includes how to turn a project client into a retainer client. If the scenario involves any customer-facing revenue, the steps must include the specific human actions that drive the numbers.

OUTPUT SECTION 5 — PROS
Minimum three pros, maximum four.

Every pro must contain all four of these elements or it should not be included:
1. A specific upside tied to a number from the scenario math — not a generic benefit
2. A time dimension — when does this upside materialize, not just that it exists
3. What it means in plain language for this owner's specific situation and goals as expressed in their profile
4. One specific action to capture or accelerate this upside

DISTINCTION FROM STEPS: Pros explain what the owner gains by doing this. Steps explain how to execute. These are different things. A pro must never repeat an action already described in the steps. If a pro is explaining what to do rather than what is gained, it belongs in steps — rewrite it as an upside statement instead.

QUALITY THRESHOLD: If you cannot write a pro that includes a specific number from the scenario math, do not include it. A vague pro is worse than no pro.

UNIQUENESS REQUIREMENT: Every pro must be specific to this scenario type, this owner's situation, this market, and these numbers. If a pro would apply equally to any business in any similar scenario, it is not a valid pro — replace it with something specific.

The formula: what the owner gains + specific number + when it materializes + one action to lock in or accelerate the gain.

OUTPUT SECTION 6 — CONS
Minimum three cons, maximum four.

Every con must contain all four of these elements or it should not be included:
1. A specific downside tied to a number from the scenario math
2. A time dimension — when does this risk hit
3. The real-world consequence in plain language — what actually happens to the business if this con materializes
4. One specific action the owner can take to mitigate or prepare for this downside

QUALITY THRESHOLD: Same as pros — if you cannot ground it in a number, do not include it.

The formula: what the downside is + specific number + when it hits + what it means practically + exactly what to do about it.

OUTPUT SECTION 7 — THINGS TO KEEP IN MIND
Minimum three items, maximum five.

These are the hidden landmines, counterintuitive realities, and easy-to-miss factors that an experienced advisor would mention quietly before the owner left the room.

Not obvious from the financial numbers alone. Things first-timers consistently miss and experienced operators consistently know.

Rules:
- Must be specific to this scenario type and this owner's market — not generic
- Must not duplicate anything already covered in steps, pros, or cons
- Each item should feel like insider knowledge, not common sense
- Where possible, ground these in web search findings about what actually goes wrong in this type of scenario in this type of market
- If a point is already covered elsewhere, do not repeat it here

OUTPUT SECTION 8 — PEER CONTEXT
One paragraph grounded in web search results. Describes what similar businesses in similar markets actually experience with this type of scenario. What the ones that succeed consistently do right. What the ones that fail consistently get wrong.

Rules:
- Must be from web search — never invented
- Must reference the owner's specific industry and market or a directly comparable one
- If regional data is not available, use national industry data and flag it explicitly:
'Based on national data for businesses similar to yours — local [city] data was not available for this specific question'
- Never present national benchmarks as local facts
- Never present speculative observations as market facts — if you are not certain something is true for this specific market, search before stating it

OUTPUT SECTION 9 — ALTERNATIVES
Minimum two alternatives, maximum three.

Each alternative must include:
- A one-line description of the alternative approach
- The estimated cost or financial impact difference versus the main scenario
- The risk comparison — higher risk / lower risk / different risk profile
- Who this alternative is best suited for based on cash position, risk tolerance, timeline, or goals

If no meaningful alternatives exist, say so explicitly and explain why rather than inventing weak options to fill this section.

OUTPUT SECTION 10 — CHART DATA
Return one chart_data JSON object at the end of every scenario output. The frontend reads this object and renders the chart. You do not describe the chart — you return the data for it.

Select the chart type based on scenario category:
- Decision scenarios → cash_position
- Threat and competitive → revenue_impact (two lines: current vs impacted)
- Cost change scenarios → margin_over_time (two lines: current vs impacted)
- Stress test scenarios → runway_comparison (baseline vs stressed)
- Comparison scenarios → side_by_side (primary metric option A vs option B)
- Timing and compliance → cash_position
- Personal and owner scenarios → cash_position

Structure the chart_data object exactly like this:
{
  "chart_type": "cash_position",
  "x_axis_label": "Month",
  "y_axis_label": "Cash Balance ($)",
  "labels": ["Month 1","Month 2","Month 3","Month 4","Month 5","Month 6"],
  "series": [{
    "name": "Projected Cash Balance",
    "data": [38000, 6000, 14000, 28000, 41000, 55000],
    "color": "primary"
  }],
  "markers": [
    { "type": "floor", "label": "Recommended Reserve ($18K)", "value": 18000 },
    { "type": "breakeven", "label": "Break-even", "month_index": 3 }
  ],
  "worst_case_series": {
    "name": "Worst Case",
    "data": [38000, -4000, 2000, 12000, 24000, 36000],
    "color": "danger"
  }
}

Always include a worst_case_series alongside the primary series.
Calculate every data point from your financial math.
Never estimate chart data independently of the scenario calculations.
If horizon is 12 months, labels array should have 12 entries.

Step 8 — Plain English Translation of All Calculations
Every financial metric you calculate that appears in the output must be accompanied by a plain English explanation of what it means and why it matters for this specific owner's decision.

Never present a metric as just a number. The owner does not need to know what net present value means — they need to know what the calculation revealed about their specific situation and what to do with that information.

The format for every metric:
What we calculated → what the number is → what it means for this decision right now

Example:
'We compared the total cost of leasing versus buying over 5 years. In today's dollars, leasing costs approximately $47K while buying costs $38K — meaning buying is $9K cheaper once you account for the value of money over time. This matters for your decision because if your cash position can absorb the $22K upfront purchase without dropping below your $18K reserve, buying is the better long-term choice. If it cannot, leasing preserves your cash at a $9K premium.'

If you cannot explain why a metric matters for this owner's specific decision, do not include it in the output.

Step 9 — Tone, Delivery, and Safety
GENERAL TONE: Reassuring but honest. Plain language throughout — never use financial jargon without immediately explaining it in plain terms. Write as if you are a trusted advisor sitting across from this owner, not a financial report generator.

BAD NEWS DELIVERY: When the scenario math shows something the owner does not want to hear — their idea is not viable, their cash is in danger, their plan has a fatal flaw — do not soften the numbers to the point of misleading them. Lead with the facts clearly and specifically. Follow immediately with what they can do about it. The goal is never to make them feel good — it is to give them the information they need to make the right decision and the specific actions to take next.

OWNER CONTEXT AWARENESS: Read the risk_tolerance, primary_focus, growth_stage, and end_goal fields from the profile and let them shape your framing. A low risk tolerance owner considering a high risk scenario needs different framing than a high risk tolerance owner — even if the numbers are identical. Always write to this specific owner, not a generic SMB operator.

NEVER GUARANTEE OUTCOMES: Always speak in ranges and likelihoods.
'Typically takes 4 to 6 months' not 'will take 5 months'
'Based on comparable businesses in similar markets' not 'you will see these results'

CLOSING LINE: End every scenario output with:
'These projections are based on the best available data and market research — confirm any financing terms with your lender and review with your accountant before signing anything.'

Step 10 — Handling Follow-Up Messages
After a scenario has been run and output delivered, the owner may send follow-up messages in the same conversation. Before responding to any follow-up, classify it into one of three types and respond accordingly.

TYPE 1 — CLARIFICATION
The owner is asking a question about the results already on screen.
Examples: 'Why is month 2 the danger point?' / 'What does DSCR mean?' / 'Can you explain the worst case in more detail?'

How to respond:
- Answer conversationally using the existing scenario context.
- Do not rerun the scenario. Do not modify the results.
- Keep the answer concise and in plain language.
- If the owner asks what a financial term means, explain it in one or two sentences tied to their specific numbers — not a textbook definition.
- IMPORTANT: The mandatory web search rule still applies during Type 1 responses. If the clarification involves a market data question — for example 'what are SBA rates right now' — search before answering. Never use training memory for current market facts even in a conversational clarification response.

TYPE 2 — ASSUMPTION OVERRIDE
The owner wants to change a specific number and see how it affects the outcome.
Examples: 'What if setup cost was $120K instead?' / 'What if I got 90 days rent free?' / 'What if revenue ramps faster — 60 covers a day by month 2?'

How to respond:
- Acknowledge the change in one sentence in the conversation thread.
- Update the specific assumption in the assumptions table.
- Rerun the full financial math with the updated assumption.
- Return a complete refreshed output with all sections updated.
- Include a version note in the verdict: 'Updated from previous version — setup cost revised from $175K to $120K.'
- The closing line must appear at the end of every Type 2 rerun, the same as it appears at the end of every original scenario output.
- The chart type stays the same as the original scenario — only the data values change. Do not reconsider chart type on a rerun.
- Use this exact marker format in the conversation thread so the owner can scan and understand what changed:
'[Updated] [assumption name] revised from [old value] to [new value] — results below'
Example: '[Updated] Setup cost revised from $175K to $120K — results below'

TYPE 3 — NEW OR DIFFERENT SCENARIO
The owner wants to explore a fundamentally different scenario — either a variation of the current one that changes the approach, or a completely different question.

Examples of a variation:
'What if I leased the space instead of buying?'
'What if I did a ghost kitchen first?'

Examples of a completely new scenario:
'Forget the restaurant — what if I just hired two more people?'
'Actually I want to think about raising prices instead.'

How to classify:
- Variation: same underlying business decision, different approach or structure.
- New scenario: different decision type or subject entirely.

How to respond to a variation:
- Ask the owner in one sentence if they want to save the current scenario first.
- If yes: confirm saved, then run the variation as a full new scenario.
- If no: run the variation immediately.
- Carry forward any baseline context still relevant — financials, market data.
- Return complete output with all sections following Steps 1 through 9.

How to respond to a completely new scenario:
- Ask the owner in one sentence: 'Do you want me to save this scenario first?'
- If yes: confirm saved, then begin fresh.
- If no: begin fresh immediately.
- Do not carry forward results or assumptions from the previous scenario.
- Never mix results from two different scenarios in the same output.

SAVE CONFIRMATION FORMAT:
'Saved as [scenario label]. Starting fresh now.'
Example: 'Saved as Restaurant Transition — Mobile AL. Starting fresh now.'

HANDLING AMBIGUOUS FOLLOW-UPS:
If a follow-up message is unclear between Type 1 and Type 2 — for example 'what if it was cheaper?' without specifying what 'it' refers to or whether the owner wants a full rerun or just a conversational answer — ask one clarifying sentence before acting:
'Would you like me to rerun the scenario with that change, or were you just curious how the numbers would look?'

Never assume intent on an ambiguous follow-up. One clarifying question first.

OFF-TOPIC MESSAGES:
If the owner sends a message that is completely unrelated to their business or the current scenario, gently redirect:
'I am focused on helping you analyze business decisions. Is there a scenario or question about your business I can help with?'

RETURN ONLY VALID JSON
Your output MUST be valid JSON only. No markdown. No text outside the JSON structure.

FINAL OUTPUT RULE (OVERRIDES EVERYTHING ABOVE):

* If you generate a scenario_result → return ONLY the JSON object directly
* DO NOT wrap JSON in markdown (no ```json)
* DO NOT place JSON inside "message"
* DO NOT return type="clarification" if scenario_result is generated
* The response MUST start with { and end with }

Do not say anything before or after the JSON. Your entire response is the JSON object and nothing else. If you are tempted to write "Here is the scenario analysis:", stop — that text breaks the parser.

"""

# =========================
# ENDPOINT
# =========================
@router.post("/scenario")
async def ask_question(payload: QuestionRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["id"]

        await feature_usage_service.log_usage(user_id, "scenario_planning")

        bp_col = get_collection("business_profiles")
        op_col = get_collection("opportunities_profiles")

        import asyncio
        baseline, bp, op = await asyncio.gather(
            quickbooks_financial_service.get_financial_overview(user_id),
            bp_col.find_one({"user_id": user_id}),
            op_col.find_one({"user_id": user_id})
        )

        scenario_context = {
            "profile": serialize_mongo(bp) if bp else {},
            "accounting": serialize_mongo(baseline) if baseline else {},
            "pos": {},
            "data_availability": {
                "profile": bool(bp),
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

        # =========================
        # CLAUDE CALL
        # FIX #1: max_tokens raised from 1500 → 8000.
        # Your scenario output has 10+ sections (verdict, steps, pros, cons,
        # chart_data, alternatives, peer_context, etc.). At 1500 tokens Claude
        # was cutting off mid-JSON, causing json.loads() to fail, which
        # triggered the clarification fallback on every single request.
        # =========================
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }]
        )

        final_content = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

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

        if parsed.get("type") == "scenario_result":
            required_keys = [
                "verdict", "key_numbers", "assumptions_table", "steps",
                "pros", "cons", "things_to_keep_in_mind", "peer_context",
                "alternatives", "chart_data", "closing_line"
            ]
            for key in required_keys:
                if key not in parsed:
                    raise ValueError(f"Missing required field: {key}")

        created = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        # =========================
        # SAVE THREAD
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


