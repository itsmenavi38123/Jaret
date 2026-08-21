from datetime import datetime, timezone
from typing import Literal, Optional, Any, Dict, List
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db import get_collection
from app.routes.auth.auth import get_current_user
from app.services.benchmark_service import benchmark_service
from app.services.dashboard_ask_service import dashboard_ask_service
from app.services.dashboard_service import dashboard_service
from app.services.kpi_ai_service import kpi_ai_service
from app.services.redis_client import get_redis_client
from app.services.reminders_service import reminders_service

router = APIRouter(tags=["dashboard"])
logger = logging.getLogger(__name__)

class DashboardAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    surface: Optional[str] = "dashboard_ask"
    chat_id: Optional[str] = None
    chat_history: Optional[List[Dict[str, Any]]] = []


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


class DashboardSummaryResponse(BaseModel):
    """Placeholder for OpenAPI docs (not enforced at runtime)."""

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


@router.post("/dashboard/kpi-explain")
async def explain_kpi_drawer(
    body: KPIDrawerExplainRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    from app.services.cost_guardrail_service import cost_guardrail_service
    allowed, reason = await cost_guardrail_service.check_and_reserve(user_id, "drawer_ask")
    if not allowed:
        detail_msg = (
            "You've reached today's limit for this action. It resets at midnight."
            if reason == "surface_cap" else
            "You've reached today's usage limit for your account. It resets at midnight. Contact support if you need more."
        )
        raise HTTPException(status_code=429, detail=detail_msg)

    try:
        business_profiles = get_collection("business_profiles")
        profile = await business_profiles.find_one({"user_id": user_id})

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
                    benchmarks = await benchmark_service.get_or_fetch_benchmarks(
                        business_type=business_type,
                        country=country,
                        annual_revenue_dollars=annual_revenue,
                    )

                    if benchmarks:
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
                    logger.warning(f"Benchmark lookup failed: {exc}")

        payload = body.model_dump()
        payload["optional_context"] = enriched_context

        try:
            result = await kpi_ai_service.explain_kpi_drawer(payload=payload)
        except Exception as e:
            await cost_guardrail_service.refund_reserve(user_id, "drawer_ask")
            raise e

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
):
    user_id = current_user["id"]
    from app.services.cost_guardrail_service import cost_guardrail_service
    allowed, reason = await cost_guardrail_service.check_and_reserve(user_id, "dashboard_ask")
    if not allowed:
        detail_msg = (
            "You've reached today's limit for this action. It resets at midnight."
            if reason == "surface_cap" else
            "You've reached today's usage limit for your account. It resets at midnight. Contact support if you need more."
        )
        raise HTTPException(status_code=429, detail=detail_msg)

    try:
        try:
            result = await kpi_ai_service.ask_kpi_ai(
                payload=body.model_dump()
            )
        except Exception as e:
            await cost_guardrail_service.refund_reserve(user_id, "dashboard_ask")
            raise e

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


@router.post("/dashboard/ask")
async def ask_dashboard_advisor(
    body: DashboardAskRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Whole-business Ask AI Advisor chatbot endpoint.
    Routes query to Claude with business context and persists conversation in MongoDB.
    """
    user_id = current_user["id"]
    from app.services.cost_guardrail_service import cost_guardrail_service
    allowed, reason = await cost_guardrail_service.check_and_reserve(user_id, "dashboard_ask")
    if not allowed:
        detail_msg = (
            "You've reached today's limit for this action. It resets at midnight."
            if reason == "surface_cap" else
            "You've reached today's usage limit for your account. It resets at midnight. Contact support if you need more."
        )
        raise HTTPException(status_code=429, detail=detail_msg)

    try:
        result = await dashboard_ask_service.ask_advisor(
            user_id=user_id,
            question=body.question,
            surface=body.surface or "dashboard_ask",
            chat_id=body.chat_id,
            chat_history=body.chat_history,
        )
    except Exception as exc:
        await cost_guardrail_service.refund_reserve(user_id, "dashboard_ask")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Ask AI Advisor response: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": result},
    )


@router.get("/dashboard/chats")
async def list_dashboard_chats(
    q: Optional[str] = Query(None, description="Optional keyword search string across title and message content"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    List past Ask AI conversations for sidebar history.
    Supports content keyword search via query parameter `?q=keyword`.
    """
    try:
        chats = await dashboard_ask_service.list_chats(
            user_id=current_user["id"],
            query=q,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch past chats: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": chats},
    )


@router.get("/dashboard/chats/{chat_id}")
async def get_dashboard_chat_thread(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve full message transcript for a specific past Ask AI chat.
    """
    try:
        chat = await dashboard_ask_service.get_chat_thread(
            user_id=current_user["id"],
            chat_id=chat_id,
        )
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat thread not found",
            )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat thread: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": chat},
    )