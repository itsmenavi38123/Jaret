from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.routes.auth.auth import get_current_user
from app.services.dashboard_service import dashboard_service
from app.services.reminders_service import reminders_service
from typing import Optional, Literal, Any, Dict, List
from app.services.openai_service import OpenAIService

router = APIRouter(tags=["dashboard"])

class KPIChatRequest(BaseModel):
    kpi_name: Literal[
        "revenue_mtd",
        "net_margin_pct",
        "cash",
        "runway_months",
        "ai_health_score"
    ]
    current_value: Optional[float] = None
    prior_value: Optional[float] = None
    question: str
    chat_history: Optional[List[Dict[str, str]]] = []
    optional_context: Optional[Dict[str, Any]] = None


class KPIDrawerContext(BaseModel):
    financial_overview: Optional[Any] = None
    benchmarks: Optional[Any] = None
    already_displayed_insights: Optional[Any] = None


class KPIDrawerExplainRequest(BaseModel):
    kpi_name: str
    current_value: Optional[float] = None
    prior_value: Optional[float] = None
    format_type: Literal["currency", "percentage", "months", "score"]
    optional_context: Optional[KPIDrawerContext] = None


class ManualEntryRequest(BaseModel):
    company_id: Optional[str] = None
    entry_type: Literal["income", "expense"]
    amount: float = Field(gt=0)
    category: str
    label: Optional[str] = None
    occurred_on: datetime
    notes: Optional[str] = None

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
    """
    Get dynamic reminders from QuickBooks data.
    
    Includes:
    - Overdue invoices
    - Upcoming bill payments
    - Pending payroll
    - Tax calendar deadlines
    
    Returns top reminders sorted by priority (overdue first) and due date.
    """
    try:
        reminders = await reminders_service.get_dynamic_reminders(
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



@router.post("/dashboard/kpi-explain")
async def explain_kpi_drawer(
    body: KPIDrawerExplainRequest,
    current_user: dict = Depends(get_current_user),
    openai_service: OpenAIService = Depends(),
):
    try:
        result = await openai_service.explain_kpi_drawer(
            payload=body.model_dump()
        )

    except ValueError as exc:
        # JSON parsing / validation error
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid AI response: {exc}",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate KPI explanation: {exc}",
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": result},
    )



@router.post("/dashboard/kpi-ask-ai")
async def ask_kpi_ai(
    body: KPIChatRequest,
    current_user: dict = Depends(get_current_user),
    openai_service: OpenAIService = Depends(),
):
    try:
        result = await openai_service.ask_kpi_ai(
            payload=body.model_dump()
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
        content=jsonable_encoder({"success": True, "data": result}),
    )