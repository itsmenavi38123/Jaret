from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.routes.auth.auth import get_current_user
from app.services.dashboard_service import dashboard_service
from app.services.quickbooks_financial_service import quickbooks_financial_service

router = APIRouter(tags=["financial-overview"])


@router.get("/financial-overview")
async def get_financial_overview(
    current_user: dict = Depends(get_current_user),
):
    """
    Aggregate a financial overview for the authenticated user's connected QuickBooks company.
    """
    try:
        overview = await quickbooks_financial_service.get_financial_overview(
            user_id=current_user["id"],
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build financial overview: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": overview}),
    )


@router.get("/dashboard/kpis")
async def get_dashboard_kpis(
    current_user: dict = Depends(get_current_user),
):
    try:
        user_id = current_user["id"]

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

