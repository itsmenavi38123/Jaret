# backend/app/routes/ai_opportunities.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import re
from app.routes.auth.auth import get_current_user
from app.db import get_collection
from app.services.research_scout_service import ResearchScoutService
from app.services.firecrawl_service import firecrawl_service
from datetime import datetime, timedelta
# from app.services.tagging_service import tagging_service
from app.services.scoring_service import scoring_service

router = APIRouter(tags=["ai-opportunities"])
research_scout = ResearchScoutService()

STOPWORDS = {
    "the", "a", "an", "and", "or","of", "for", "in", "at", "to"
    }

def normalize_query(query: str) -> str:
    query = query.lower()
    query = re.sub(r"[^\w\s]", " ", query)
    query = re.sub(r"\b(2024|2025|2026)\b", " ", query)

    words = [
        word for word in query.split()
        if word not in STOPWORDS
    ]

    words.sort()

    return " ".join(words)

def normalize_opportunity_title(title: str) -> str:
    return normalize_query(title)

async def process_scout_output(
    user_id: str,
    result: Dict[str, Any],
) -> Dict[str, int]:

    opportunities = get_collection("opportunities")

    dedup_skipped = 0
    tracked_skipped = 0

    tracked_opportunities = await opportunities.find(
        {
            "user_id": user_id,
            "status_user": {
                "$in": [
                    "tracked",
                    "applied",
                    "selected",
                ]
            }
        },
        {
            "_id": 1,
            "normalized_title": 1,
        }
    ).to_list(length=None)

    tracked_titles = {
        item.get("normalized_title")
        for item in tracked_opportunities
    }

    cards = result.get("opportunities", {}).get("cards", [])

    for card in cards:

        normalized_title = normalize_opportunity_title(
            card.get("title", "")
        )

        if normalized_title in tracked_titles:

            tracked_skipped += 1

            continue

        geo = card.get("geo", {})

        city = geo.get("city")
        state = geo.get("state")

        deadline = card.get("deadline")
        start_date = card.get("start_date")

        opportunity_type = card.get("opportunity_type")
        event_metadata = {
            "event_prestige_tier": card.get("event_prestige_tier"),
            "event_audience": card.get("event_audience"),
            "event_service_fit": card.get("event_service_fit", []),
        }

        risk_data = {
            "adjacent_match": card.get("adjacent_match", False),
        }

        scoring_data = {
            "industry_jaccard_score": card.get(
                "industry_jaccard_score",
                0,
            ),
        }

        portfolio_data = {
            "business_tags": card.get("business_tags", []),
            "opportunity_tags": card.get("opportunity_tags", []),

            "service_model": card.get("service_model"),
            "price_tier": card.get("price_tier"),
            "audience": card.get("event_audience") or card.get("audience"),

            "proven_capabilities": card.get("proven_capabilities", []),
            "historical_outcomes": card.get("historical_outcomes", []),
        }
        dedup_query = {
            "user_id": user_id,
            "normalized_title": normalized_title,
            "geo.city": city,
            "geo.state": state,
            "opportunity_type": opportunity_type,
        }

        if deadline:
            dedup_query["deadline"] = deadline

        elif start_date:
            dedup_query["start_date"] = start_date

        existing = await opportunities.find_one(
            dedup_query
        )

        weather_snapshot = (
            card.get("weather_data", {})
            .get("weather_snapshot", {})
        )

        severe_weather_flag = (
            weather_snapshot.get(
                "severe_weather_flag",
                False,
            )
        )

        weather_risk_message = None

        if severe_weather_flag:
            weather_risk_message = (
                weather_snapshot.get("summary")
                or "Severe weather risk detected."
            )

        business_context = {
            "business_classifications": card.get(
                "business_classifications",
                [],
            ),
        }

        scoring_result = scoring_service.score_opportunity(
            opportunity=card,
            business_context=business_context,
            trigger="initial_scout",
        )
        why_reason_codes = []

        if card.get("adjacent_match"):
            why_reason_codes.append("adjacent_industry_match")

        if card.get("industry_jaccard_score", 0) >= 0.5:
            why_reason_codes.append("strong_industry_match")

        if card.get("event_prestige_tier") in [
            "premium",
            "elite",
        ]:
            why_reason_codes.append("high_prestige_event")

        if card.get("event_audience") == "b2b":
            why_reason_codes.append("b2b_alignment")

        if card.get("weather_badge") == "good":
            why_reason_codes.append("favorable_weather")

        update_data = {
            **card,
            "user_id": user_id,
            "normalized_title": normalized_title,
            "updated_at": datetime.utcnow(),

            "match_score": scoring_result["match_score"],
            "readiness_score": scoring_result["readiness_score"],
            "portfolio_adjusted_readiness": scoring_result.get("portfolio_adjusted_readiness"),
            "event_readiness_score": scoring_result["event_readiness_score"],
            "event_readiness_label": scoring_result.get("event_readiness_label"),
            "data_trust_indicator": scoring_result["data_trust_indicator"],
            "last_scored_at": scoring_result["last_scored_at"],
            "why_reason_codes": scoring_result.get("why_reason_codes", []),
            "expected_roi_mult": scoring_result.get("expected_roi_mult"),
            "expected_roi_display": scoring_result.get("expected_roi_display"),
            "event_metadata": event_metadata,

            "risk_data": {
                **card.get("risk_data", {}),
                **risk_data,
                "why_reason_codes": why_reason_codes,
            },

            "scoring_data": {
                **card.get("scoring_data", {}),
                **scoring_data,

                "score_history": [
                    *(existing.get("scoring_data", {}).get("score_history", []) if existing else []),
                    *scoring_result["score_history"],
                ],

                "original_preliminary_fit_score": (
                    existing.get("scoring_data", {}).get(
                        "original_preliminary_fit_score",
                        card.get("fit_score", 0),
                    )
                    if existing
                    else card.get("fit_score", 0)
                ),
            },

            "portfolio_data": {
                **card.get("portfolio_data", {}),
                **portfolio_data,
            },

            "weather_data": {
                **card.get("weather_data", {}),
                "weather_risk_detected": severe_weather_flag,
                "weather_risk_message": weather_risk_message,
            },

            "verification_data": {
                **card.get("verification_data", {}),
                "data_trust_indicator": scoring_result["data_trust_indicator"],
            },
        }

        if existing:

            await opportunities.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": update_data
                }
            )

            dedup_skipped += 1

            continue

        update_data["created_at"] = datetime.utcnow()
        update_data["ingested_at"] = datetime.utcnow()

        await opportunities.insert_one(update_data)

    return {
        "dedup_skipped": dedup_skipped,
        "tracked_skipped": tracked_skipped,
    }

async def firecrawl_search(search_term: str, recency_days: int = 30, max_results: int = 10,) -> List[Dict[str, Any]]:

    try:
        results = await firecrawl_service.search(
            query=search_term,
            recency_days=recency_days,
            max_results=max_results,
        )

        return results

    except Exception as e:
        print(f"firecrawl_search error: {e}")
        return []

async def firecrawl_scrape(url: str) -> Dict[str, Any]:

    try:
        result = await firecrawl_service.scrape(url=url)
        return result

    except Exception as e:
        print(f"firecrawl_scrape error: {e}")
        return {"url": None, "markdown": None, "metadata": {}, "success": False}
    
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
    try:
        user_id = current_user["id"]
        scout_rate_limits = get_collection("scout_rate_limits")
        scout_cache = get_collection("scout_query_cache")
        scout_runs = get_collection("scout_runs")
        today = datetime.utcnow().strftime("%Y-%m-%d")
        now = datetime.utcnow()

        rate_limit = await scout_rate_limits.find_one({"business_id": user_id , "date": today})

        if rate_limit and rate_limit.get("on_demand_count", 0) >= 10:
            raise HTTPException(
                status_code=429,
                detail="Daily Scout search limit reached.",
            )
        normalized_query = normalize_query(request.query)

        cached_result = await scout_cache.find_one({
            "business_id": user_id,
            "normalized_query": normalized_query,
            "expires_at": {
                "$gt": now
            }
        })

        if cached_result:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=jsonable_encoder(
                    cached_result["response"]
                ),
                media_type="application/json",
            )

        from app.services.cost_guardrail_service import cost_guardrail_service
        allowed, reason = await cost_guardrail_service.check_and_reserve(user_id, "scout_ondemand")
        if not allowed:
            detail_msg = (
                "You've reached today's limit for this action. It resets at midnight."
                if reason == "surface_cap" else
                "You've reached today's usage limit for your account. It resets at midnight. Contact support if you need more."
            )
            raise HTTPException(status_code=429, detail=detail_msg)

        try:
            business_profiles = get_collection("business_profiles")
            business_profile = await business_profiles.find_one({"user_id": user_id})

            opportunities_profiles = get_collection("opportunities_profiles")
            opportunities_profile = await opportunities_profiles.find_one({"user_id": user_id})
            
            result = await research_scout.search_opportunities(
                query=request.query,
                user_id=user_id,
                business_profile=business_profile,
                opportunities_profile=opportunities_profile,
                mode=mode,
            )
        except Exception as e:
            await cost_guardrail_service.refund_reserve(user_id, "scout_ondemand")
            raise e

        if ( result.get("opportunities") and result["opportunities"].get("cards")):
            result["opportunities"]["cards"] = (result["opportunities"]["cards"][:8])

        pipeline_stats = await process_scout_output(
            user_id=user_id,
            result=result,
        )

        await scout_runs.insert_one({
            "business_id": user_id,
            "run_type": "on_demand",
            "user_query": request.query,
            "started_at": now,
            "completed_at": now,
            "status": "completed",
            "cards_returned": len(
                result.get("opportunities", {}).get("cards", [])
            ),
            "queries_run": [request.query],
            "types_searched": request.opportunity_types or [],
            "dedup_skipped": pipeline_stats["dedup_skipped"],
            "tracked_skipped": pipeline_stats["tracked_skipped"],
        })

        await scout_rate_limits.update_one(
            {
                "business_id": user_id,
                "date": today,
            },
            {
                "$inc": {
                    "on_demand_count": 1
                },
                "$set": {
                    "last_search_at": now,
                }
            },
            upsert=True,
        )
        await scout_cache.update_one(
            {
                "business_id": user_id,
                "normalized_query": normalized_query,
            },
            {
                "$set": {
                    "response": result,
                    "expires_at": now + timedelta(hours=24),
                    "updated_at": now,
                }
            },
            upsert=True,
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(result),
            media_type="application/json",
        )
    
    except HTTPException:
        raise

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
    opp_types_list = opportunity_types.split(",") if opportunity_types else None
    
    request = OpportunitySearchRequest(
        query=query,
        opportunity_types=opp_types_list,
        limit=limit,
    )
    
    return await ai_opportunities_search(request, current_user, mode)

@router.get("/event-readiness-kpi")
async def get_event_readiness_kpi(
    current_user: dict = Depends(get_current_user),
):

    try:
        opportunities = get_collection("opportunities")
        user_id = current_user["id"]
        now = datetime.utcnow()
        next_30_days = now + timedelta(days=30)
        upcoming_events = await opportunities.find(
            {
                "user_id": user_id,
                "type": "event",
                "start_date": {
                    "$gte": now.isoformat(),
                    "$lte": next_30_days.isoformat(),
                },
                "event_readiness_score": {
                    "$ne": None,
                },
            }
        ).to_list(length=None)

        fallback_used = False

        if not upcoming_events:

            next_120_days = now + timedelta(days=120)
            upcoming_events = await opportunities.find(
                {
                    "user_id": user_id,
                    "type": "event",
                    "start_date": {
                        "$gte": now.isoformat(),
                        "$lte": next_120_days.isoformat(),
                    },
                    "event_readiness_score": {
                        "$ne": None,
                    },
                }
            ).to_list(length=None)
            fallback_used = True

        if not upcoming_events:

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": "No upcoming events.",
                    "event_readiness_index": None,
                    "events_count": 0,
                },
            )

        scores = [
            event.get("event_readiness_score", 0)
            for event in upcoming_events
            if event.get("event_readiness_score") is not None
        ]

        average_score = round(sum(scores) / max(len(scores), 1))

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "event_readiness_index": average_score,
                "events_count": len(scores),
                "fallback_120d_used": fallback_used,
            },
        )

    except Exception as e:

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": str(e),
            },
        )