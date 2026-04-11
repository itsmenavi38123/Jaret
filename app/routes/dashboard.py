from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import re
from app.routes.auth.auth import get_current_user
from app.services.dashboard_service import dashboard_service
from app.services.reminders_service import reminders_service
from app.services.benchmark_service import benchmark_service
from app.db import get_collection
from typing import Optional, Literal, Any, Dict, List
from app.services.openai_service import OpenAIService
import logging
from app.services.redis_client import get_redis_client
import json

router = APIRouter(tags=["dashboard"])
logger = logging.getLogger(__name__)

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
        summary = await dashboard_service.get_dashboard_summary(
            user_id=current_user["id"]
        )

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
        business_profiles = get_collection("business_profiles")
        profile = await business_profiles.find_one({"user_id": current_user["id"]})

        enriched_context = body.optional_context.model_dump() if body.optional_context else {}

        redis_client = await get_redis_client()

        def parse_revenue(value):
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            value = re.sub(r"[^\d.]", "", str(value))  # remove $, commas
            return float(value) if value else None

        if profile and profile.get("onboarding_data") and redis_client:
            onboarding = profile["onboarding_data"]

            business_type = (
                onboarding.get("industry_description")
                or onboarding.get("industry")
                or onboarding.get("business_type")
            )

            monthly_revenue = onboarding.get("monthly_revenue")
            monthly = parse_revenue(monthly_revenue)
            annual_revenue = monthly * 12 if monthly else None

            country = onboarding.get("country", "US")

            if business_type and annual_revenue:
                try:
                    revenue_band = benchmark_service._calculate_revenue_band(annual_revenue)

                    cache_key = benchmark_service._build_cache_key(
                        business_type=business_type,
                        country=country,
                        revenue_band=revenue_band,
                    )

                    print(" KPI CACHE KEY:", cache_key)

                    cached = await redis_client.get(cache_key)

                    if cached:
                        print("🔥 KPI CACHE HIT")

                        benchmarks = json.loads(cached)

                        kpi_to_metric = {
                            "current_ratio": "current_ratio",
                            "quick_ratio": "quick_ratio",
                            "debt_to_equity": "debt_to_equity",
                            "interest_coverage": "interest_coverage",
                            "dso": "dso",
                            "dpo": "dpo",
                            "inventory_turnover": "inventory_turnover",
                            "cash_conversion_cycle": "cash_conversion_cycle",
                            "revenue_growth_rate": "revenue_growth_rate",
                            "revenue_mtd": "revenue_growth_rate",
                            "net_profit_margin": "net_profit_margin",
                            "net_margin_pct": "net_profit_margin",
                            "operating_cash_flow_margin": "operating_cash_flow_margin",
                            "cash_runway": "cash_runway",
                            "runway_months": "cash_runway",
                            "cash": "cash_runway",
                        }

                        metric_name = kpi_to_metric.get(body.kpi_name.lower())

                        if metric_name and metric_name in benchmarks:
                            metric_data = benchmarks.get(metric_name)

                            if metric_data and metric_data.get("median") is not None:
                                enriched_context["benchmarks"] = {
                                    metric_name: metric_data
                                }

                except Exception as exc:
                    logger.warning(f"Benchmark cache read failed: {exc}")

        payload = body.model_dump()
        payload["optional_context"] = enriched_context

        result = await openai_service.explain_kpi_drawer(payload=payload)

    except ValueError as exc:
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