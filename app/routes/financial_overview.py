from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.routes.auth.auth import get_current_user
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.services.dashboard_service import dashboard_service

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
    """
    Get dashboard KPI cards with values, deltas, colors, and links.
    Returns: Revenue MTD, Net Margin %, Cash, Runway (months), AI Health Score.
    """
    try:
        dashboard_data = await dashboard_service.get_dashboard_data(
            user_id=current_user["id"],
        )
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

