from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.routes.auth.auth import get_current_user
from app.services.dashboard_service import dashboard_service
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.services.financial_overview_service import financial_overview_service

router = APIRouter(tags=["financial-overview"])
from app.services.benchmark_service import benchmark_service
from app.models.financial_overview_drawer import (
    FinancialOverviewDrawerRequest,
    FinancialOverviewAskAIRequest,
)

from app.services.financial_overview_drawer_service import financial_overview_drawer_service
from app.services.financial_overview_kpi_preferences_service import financial_overview_kpi_preferences_service
from app.models.financial_overview_kpi_preferences_request import FinancialOverviewKPIPreferencesRequest

from fastapi.encoders import jsonable_encoder

from app.db import get_collection
import re

# @router.get("/financial-overview")
# async def get_financial_overview(
#     current_user: dict = Depends(get_current_user),
# ):
#     """
#     Aggregate a financial overview for the authenticated user's connected QuickBooks company.
#     """
#     try:
#         overview = await quickbooks_financial_service.get_financial_overview(
#             user_id=current_user["id"],
#         )
#     except HTTPException as exc:
#         raise exc
#     except Exception as exc:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to build financial overview: {exc}",
#         ) from exc

#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content=jsonable_encoder({"success": True, "data": overview}),
#     )


@router.get("/dashboard/kpis")
async def get_dashboard_kpis(
    current_user: dict = Depends(get_current_user),
):
    try:
        user_id = current_user["id"]

        try:
            business_profiles = get_collection("business_profiles")
            profile = await business_profiles.find_one({"user_id": user_id})

            if profile and profile.get("onboarding_data"):
                onboarding = profile["onboarding_data"]

                business_type = (
                    onboarding.get("industry_description")
                    or onboarding.get("industry")
                    or onboarding.get("business_type")
                )

                def parse_revenue(value):
                    if value is None:
                        return None
                    if isinstance(value, (int, float)):
                        return float(value)
                    value = re.sub(r"[^\d.]", "", str(value))  # remove $, commas
                    return float(value) if value else None

                monthly_revenue = onboarding.get("monthly_revenue")
                monthly = parse_revenue(monthly_revenue)
                annual_revenue = monthly * 12 if monthly else None

                country = onboarding.get("country", "US")

                if business_type and annual_revenue:
                    print("🚀 PRELOADING BENCHMARK CACHE")

                    await benchmark_service.get_or_fetch_benchmarks(
                        business_type=business_type,
                        country=country,
                        annual_revenue_dollars=annual_revenue,
                    )

                    print("✅ BENCHMARK CACHE READY")
                else:
                    print("❌ Missing business_type or annual_revenue")

            else:
                print("❌ No onboarding_data found")

        except Exception as e:
            print("⚠️ BENCHMARK PRELOAD FAILED:", e)

        # 🔥 STEP 2: FETCH KPI DATA
        summary = await dashboard_service.get_dashboard_summary(user_id=user_id)
        summary_kpis = summary.get("kpis", {})

        def build_card(kpi_key: str):
            card = summary_kpis.get(kpi_key, {})
            return {
                "value": card.get("value"),
                "prior_value": card.get("prior_value"),
            }

        kpi_cards = {
            "revenue_mtd": build_card("revenue_mtd"),
            "net_margin_pct": build_card("net_margin_pct"),
            "cash": build_card("cash"),
            "runway_months": build_card("runway_months"),
            "ai_health_score": build_card("ai_health_score"),
        }

        dashboard_data = {
            "kpis": kpi_cards,
        }

    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard KPIs: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": dashboard_data}),
    )


@router.get("/ai/insights/latest")
async def get_latest_ai_insights(
    current_user: dict = Depends(get_current_user),
):
    """
    Get top 3 AI-generated insights: strength, issue, opportunity.
    Uses Orchestrator, Finance Analyst, and Research Scout agents.
    """
    try:
        insights_data = await dashboard_service.get_ai_dashboard_insights(
            user_id=current_user["id"],
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI insights: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": insights_data}),
    )


@router.get("/dashboard/alerts")
async def get_dashboard_alerts(
    current_user: dict = Depends(get_current_user),
):
    """
    Get contextual alerts based on financial thresholds.
    Returns alerts for: low cash, margin drop, negative cash flow, etc.
    """
    try:
        alerts_data = await dashboard_service.get_contextual_alerts(
            user_id=current_user["id"],
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard alerts: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": alerts_data}),
    )


@router.get("/financial-overview")
async def get_financial_overview_v2(
    current_user: dict = Depends(get_current_user),
):
    data = await financial_overview_service.get_financial_overview_v2(
        user_id=current_user["id"],
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {
                "success": True,
                "data": data,
            }
        ),
    )


@router.post("/financial-overview/drawer")
async def get_financial_overview_drawer(
    body: FinancialOverviewDrawerRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        result = await financial_overview_drawer_service.explain(
            payload=body.model_dump(),
        )

    except HTTPException as exc:
        raise exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate drawer data: {exc}",
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": result,
        },
    )


@router.post("/financial-overview/ask-ai")
async def ask_financial_overview_ai(
    body: FinancialOverviewAskAIRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        result = await financial_overview_drawer_service.ask_ai(
            payload=body.model_dump(),
        )

    except HTTPException as exc:
        raise exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI response: {exc}",
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {
                "success": True,
                "data": result,
            }
        ),
    )

@router.get("/financial-overview/kpi-preferences")
async def get_financial_overview_kpi_preferences(
    current_user: dict = Depends(get_current_user),
):
    result = await financial_overview_kpi_preferences_service.get_preferences(
        user_id=current_user["id"],
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {
                "success": True,
                "data": result,
            }
        ),
    )

@router.post("/financial-overview/kpi-preferences")
async def save_financial_overview_kpi_preferences(
    body: FinancialOverviewKPIPreferencesRequest,
    current_user: dict = Depends(get_current_user),
):
    result = await financial_overview_kpi_preferences_service.save_preferences(
        user_id=current_user["id"],
        hidden_metric_ids=body.hidden_metric_ids,
        pinned_metric_ids=body.pinned_metric_ids,
        tile_order=body.tile_order,
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(
            {
                "success": True,
                "data": result,
            }
        ),
    )