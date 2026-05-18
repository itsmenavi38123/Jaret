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
from app.services.tagging_service import tagging_service


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
            card.get("opportunity_name", "")
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
            "business_tags": card.get(
                "business_tags",
                [],
            ),
            "opportunity_tags": card.get(
                "opportunity_tags",
                [],
            ),
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

        update_data = {
            **card,
            "user_id": user_id,
            "normalized_title": normalized_title,
            "updated_at": datetime.utcnow(),

            "event_metadata": event_metadata,

            "risk_data": {
                **card.get("risk_data", {}),
                **risk_data,
            },

            "scoring_data": {
                **card.get("scoring_data", {}),
                **scoring_data,
            },

            "portfolio_data": {
                **card.get("portfolio_data", {}),
                **portfolio_data,
            },

            "weather_data": {
                **card.get("weather_data", {}),
                "weather_risk_detected": severe_weather_flag,
                "weather_risk_message": weather_risk_message,
            }
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

