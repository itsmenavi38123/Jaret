from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.routes.auth.auth import get_current_user
from app.services.dashboard_service import dashboard_service

router = APIRouter(tags=["dashboard"])


class DashboardSummaryResponse(BaseModel):
    """Placeholder for OpenAPI docs (not enforced at runtime)."""


class QuickForecastRequest(BaseModel):
    company_id: Optional[str] = Field(
        default=None,
        description="Optional company identifier (currently inferred from auth).",
    )
    horizon_days: int = Field(
        default=30,
        ge=30,
        le=90,
        description="Forecast horizon in days (30, 60, or 90).",
    )


class ManualEntryRequest(BaseModel):
    company_id: Optional[str] = None
    entry_type: Literal["income", "expense"]
    amount: float = Field(gt=0)
    category: str
    label: Optional[str] = None
    occurred_on: datetime
    notes: Optional[str] = None


class GeminiExplainRequest(BaseModel):
    company_id: Optional[str] = None
    persona: Optional[Literal["new_owner", "experienced", "banker"]] = None


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
):
    """
    Consolidated dashboard payload with KPIs, alerts, badges, insights, and reminders.
    """
    try:
        summary = await dashboard_service.get_dashboard_summary(user_id=current_user["id"])
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build dashboard summary: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": summary}),
    )


@router.get("/dashboard/reminders")
async def get_dashboard_reminders(
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user),
):
    try:
        reminders = await dashboard_service.get_reminders(
            user_id=current_user["id"],
            limit=limit,
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch reminders: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": reminders}),
    )


@router.post("/dashboard/quick-forecast")
async def post_dashboard_quick_forecast(
    body: QuickForecastRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        forecast = await dashboard_service.run_quick_forecast(
            user_id=current_user["id"],
            horizon_days=body.horizon_days,
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quick forecast: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": forecast}),
    )


@router.post("/manual-entry")
async def post_manual_entry(
    body: ManualEntryRequest,
    current_user: dict = Depends(get_current_user),
):
    occurred_on = body.occurred_on
    if occurred_on.tzinfo is None:
        occurred_on = occurred_on.replace(tzinfo=timezone.utc)

    try:
        entry = await dashboard_service.record_manual_entry(
            user_id=current_user["id"],
            entry_type=body.entry_type,
            amount=body.amount,
            category=body.category,
            label=body.label or body.category,
            occurred_on=occurred_on,
            notes=body.notes,
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record manual entry: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder({"success": True, "data": entry}),
    )


@router.post("/ai/dashboard-insights")
async def post_ai_dashboard_insights(
    current_user: dict = Depends(get_current_user),
):
    try:
        insights = await dashboard_service.get_ai_dashboard_insights(user_id=current_user["id"])
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build AI insights: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": insights}),
    )


@router.post("/gemini/dashboard-explain")
async def post_gemini_dashboard_explain(
    body: GeminiExplainRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        explanation = await dashboard_service.explain_dashboard_with_gemini(
            user_id=current_user["id"],
            persona=body.persona,
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Gemini dashboard explanation: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": explanation}),
    )


@router.post("/gemini/ai-health-explain")
async def post_gemini_ai_health_explain(
    current_user: dict = Depends(get_current_user),
):
    try:
        explanation = await dashboard_service.explain_ai_health_with_gemini(
            user_id=current_user["id"],
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI health explanation: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": explanation}),
    )

