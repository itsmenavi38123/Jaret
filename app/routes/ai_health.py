import os
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
from app.routes.auth.auth import get_current_user
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.services.feature_usage_service import feature_usage_service
from app.services.orchestrator_service import OrchestratorService
from datetime import datetime
from app.services.business_health_engine_service import business_health_engine_service
import traceback
router = APIRouter(tags=["ai-health"])
orchestrator_service = OrchestratorService()

async def generate_watch_area_explanation(watch_areas: List[str]) -> str:
    """Generate soft-English explanation for priority watch areas (fallback to local text)."""
    if not watch_areas:
        return None
    watch_list = "; ".join(watch_areas)
    if len(watch_areas) == 1:
        local_explanation = f"Key risk: {watch_areas[0]}. Review it now and put a corrective action in place this week."
    else:
        local_explanation = (
            f"Top watch areas are: {watch_list}. We recommend fixing the highest-impact issue first and monitoring weekly."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return local_explanation

    try:
        client = AsyncOpenAI(api_key=api_key)
        prompt = (
            "You are a concise business advisor. "
            
            "Given prioritized watch areas for a small business, return exactly 3 short bullet points: 1) what it means, 2) where to focus, 3) what to do next. "
            "Use minimal words and no paragraph text. "
            "Input watch areas:\n"
            + "\n".join(f"- {area}" for area in watch_areas)
            + "\nOutput only plain text, with bullets in this format: '- ...'."
        )
        completion = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a friendly business advisor."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=220,
            temperature=0.2,
        )
        message_obj = completion.choices[0].message
        text = message_obj.content.strip() if getattr(message_obj, "content", None) else ""
        # Ensure short bullet format. If model output is too long, fallback to local bullet text.
        if text:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            bullet_lines = [line for line in lines if line.startswith("-") or line.startswith("*")]
            if len(bullet_lines) >= 2:
                return "\n".join(bullet_lines[:3])
            # If not bullet output, keep first 3 short sentences
            parts = [p.strip() for p in text.replace(". ", ".\n").splitlines() if p.strip()]
            filtered = [p for p in parts if len(p) > 5][:3]
            if filtered:
                return "\n".join(filtered)
    except Exception as e:
        print("[DEBUG] generate_watch_area_explanation exception:", repr(e))

    return local_explanation



@router.get("/full")
async def get_business_health_full(
    range: str = Query("12m"),
    include_peers: bool = Query(True),
    include_breakdowns: bool = Query(True),
    current_user: dict = Depends(get_current_user),
):
    """
    Get comprehensive Business Health Scorecard.
    Returns Financial, Operational, Customer, Risk, and Growth health metrics.
    Uses ONLY real data from QuickBooks and AI-generated insights.
    NO dummy/placeholder data.
    """
    try:
        user_id = current_user["id"]
        
        # 1. Fetch Real Financial Data from QuickBooks
        qs = quickbooks_financial_service
        
        # Get comprehensive financial overview
        financial_overview = {}
        try:
            financial_overview = await qs.get_financial_overview(user_id) or {}
        except Exception:
            financial_overview = {}
        kpis = financial_overview.get("kpis", {})
        
        # Extract Real Metrics
        revenue_mtd = kpis.get("revenue_mtd", 0.0)
        margin_pct = kpis.get("net_margin_pct")
        cash_flow_mtd = kpis.get("cash_flow_mtd")
        runway_months = kpis.get("runway_months")
        gross_margin_pct = kpis.get("gross_margin_pct")
        opex_ratio_pct = kpis.get("opex_ratio_pct")
        
        # Get liquidity metrics
        liquidity = financial_overview.get("liquidity", {})
        current_ratio = liquidity.get("current_ratio")
        quick_ratio = liquidity.get("quick_ratio")
        
        # Get efficiency metrics
        efficiency = financial_overview.get("efficiency", {})
        inventory_turns = efficiency.get("inv_turns")
        dso_days = efficiency.get("dso_days")
        ccc_days = efficiency.get("ccc_days")
        
        # Get cashflow data
        cashflow = financial_overview.get("cashflow", {})
        burn_rate_monthly = cashflow.get("burn_rate_monthly")
        net_trend_3mo = cashflow.get("net_trend_3mo")
        
        # Get calculation values for context
        calc_values = financial_overview.get("calculation_values", {})
        cash = calc_values.get("cash", 0.0)
        
        # 2. Calculate Category Scores based on REAL data
        engine_result = await business_health_engine_service.generate_business_health(
            user_id=user_id,
            financial_overview={
                "Real Data Metrics": {
                    "net_margin_pct": margin_pct,
                    "runway_months": runway_months,
                    "quick_ratio": quick_ratio,
                    "inventory_turns": inventory_turns,
                    "ccc_days": ccc_days,
                    "trend_3mo": net_trend_3mo,
                }
            }
        )

        engine_result = engine_result or {}
        overall_data = engine_result.get("overall") or {}
        financial_health = engine_result.get("financial_health") or {}
        operational_health = engine_result.get("operational_health") or {}
        risk_health = engine_result.get("risk_health") or {}
        growth_health = engine_result.get("growth_health") or {}

        if not isinstance(overall_data, dict):
            overall_data = {}

        if not isinstance(financial_health, dict):
            financial_health = {}

        if not isinstance(operational_health, dict):
            operational_health = {}

        if not isinstance(risk_health, dict):
            risk_health = {}

        if not isinstance(growth_health, dict):
            growth_health = {}

        overall_score = overall_data.get("score")
        overall_label = overall_data.get("label")

        fin_health_score = financial_health.get("score")
        fin_label = financial_health.get("label")

        ops_score = operational_health.get("score")
        ops_label = operational_health.get("label")

        risk_score = risk_health.get("score")
        risk_label = risk_health.get("label")

        growth_score = growth_health.get("score")
        growth_label = growth_health.get("label")

        margin_display = f"{margin_pct*100:.1f}%" if margin_pct is not None else "N/A"
        runway_display = f"{runway_months:.1f} mo" if runway_months is not None else "N/A"

        fin_summary = f"Net margin {margin_display}; Runway {runway_display}" if fin_health_score is not None else "Insufficient financial data"

        ops_summary = (
            f"Cash conversion cycle at {ccc_days:.0f} days"
            if ccc_days is not None
            else (
                f"Inventory turnover at {inventory_turns:.1f}x"
                if inventory_turns is not None
                else "Insufficient operational data"
            )
        )

        if risk_score is not None:
            if runway_months is not None:
                risk_summary = f"Cash runway at {runway_months:.1f} months"
                risk_missing_notice = None
            elif quick_ratio is not None:
                risk_summary = f"Quick ratio at {quick_ratio:.2f}"
                risk_missing_notice = "Cash runway data is unavailable."
            else:
                risk_summary = "Risk metrics available"
                risk_missing_notice = "Additional financial data is required to fully assess risk exposure."
        else:
            risk_summary = "Insufficient risk data"
            risk_missing_notice = "Connect financial data sources to calculate risk exposure."

        if net_trend_3mo == "positive":
            growth_summary = "Steady upward trend"
        elif net_trend_3mo == "negative":
            growth_summary = "Declining trend"
        else:
            growth_summary = "Insufficient growth data"

        cust_score = None
        cust_label = None
        cust_summary = "Insufficient customer data"

        # 4. Calculate Drivers and Drags from REAL data
        positive_drivers = []
        drags = []
        
        # Analyze margin contribution
        if margin_pct is not None:
            if margin_pct > 0.15:
                points = round((margin_pct - 0.15) * 100 * 2)
                positive_drivers.append({
                    "name": f"Healthy margins ({margin_pct*100:.1f}%)",
                    "points": f"+{points} pts"
                })
            elif margin_pct < 0.05:
                points = round((0.05 - margin_pct) * 100 * 2)
                drags.append({
                    "name": f"Low margins ({margin_pct*100:.1f}%)",
                    "points": f"-{points} pts"
                })
        
        # Analyze liquidity contribution
        if quick_ratio is not None:
            if quick_ratio > 1.5:
                points = round((quick_ratio - 1.5) * 10)
                positive_drivers.append({
                    "name": f"Strong liquidity (Quick ratio: {quick_ratio:.2f})",
                    "points": f"+{points} pts"
                })
            elif quick_ratio < 1.0:
                points = round((1.0 - quick_ratio) * 15)
                drags.append({
                    "name": f"Weak liquidity (Quick ratio: {quick_ratio:.2f})",
                    "points": f"-{points} pts"
                })
        
        # Analyze inventory efficiency
        if inventory_turns is not None:
            if inventory_turns < 4:
                points = round((4 - inventory_turns) * 3)
                drags.append({
                    "name": f"Low inventory turns ({inventory_turns:.1f}x)",
                    "points": f"-{points} pts"
                })
            elif inventory_turns > 8:
                points = round((inventory_turns - 8) * 2)
                positive_drivers.append({
                    "name": f"High inventory efficiency ({inventory_turns:.1f}x)",
                    "points": f"+{points} pts"
                })
        
        # Analyze cash conversion cycle
        if ccc_days is not None:
            if ccc_days > 60:
                points = round((ccc_days - 60) / 5)
                drags.append({
                    "name": f"Slow cash conversion ({ccc_days:.0f} days)",
                    "points": f"-{points} pts"
                })
        
        # Analyze growth trend
        if net_trend_3mo == "positive":
            positive_drivers.append({
                "name": "Positive revenue trend",
                "points": "+8 pts"
            })
        elif net_trend_3mo == "negative":
            drags.append({
                "name": "Declining revenue trend",
                "points": "-8 pts"
            })
        
        # 5. Priority Watch Areas (based on real metrics)
        priority_watch_areas = []

        if inventory_turns is not None and inventory_turns < 4:
            priority_watch_areas.append(
                f"Inventory turnover is low at {inventory_turns:.1f}x, which may slow cash recovery and increase holding costs."
            )

        if ccc_days is not None and ccc_days > 60:
            priority_watch_areas.append(
                f"Cash conversion cycle is elevated at {ccc_days:.0f} days, delaying cash returning into the business."
            )

        if quick_ratio is not None and quick_ratio < 1.0:
            priority_watch_areas.append(
                f"Quick ratio is below 1.0 ({quick_ratio:.2f}), which may create short-term cash pressure."
            )

        if runway_months is not None and runway_months < 6:
            priority_watch_areas.append(
                f"Cash runway is below 6 months ({runway_months:.1f} months remaining), limiting financial flexibility."
            )

        if margin_pct is not None and margin_pct < 0.10:
            priority_watch_areas.append(
                f"Net margin is below target at {margin_pct*100:.1f}%, reducing profitability cushion."
            )

        if growth_score is not None and growth_score < 60:
            priority_watch_areas.append(
                "Revenue trend has weakened over recent months, which may impact near-term growth momentum."
            )

        # Soft English explanation for watch areas
        watch_area_explanation = await generate_watch_area_explanation(priority_watch_areas)

        # 5.a Ranked drivers for API consumers
        ranked_drivers = []
        for d in positive_drivers:
            metric_key = "financial.net_margin"

            if "liquidity" in d["name"].lower():
                metric_key = "financial.quick_ratio"

            ranked_drivers.append({
                "type": "positive",
                "metric": metric_key,
                "points": int(d["points"].replace("+", "").replace(" pts", "")) if isinstance(d.get("points"), str) and d["points"].startswith("+") else 0,
                "detail": d["name"],
                "sub_metric_data": {
                    "margin_pct": margin_pct,
                    "quick_ratio": quick_ratio,
                    "inventory_turns": inventory_turns,
                    "ccc_days": ccc_days,
                    "trend_3mo": net_trend_3mo,
                }
            })

        for d in drags:
            metric_key = "operational.inventory_turnover"

            if "cash conversion" in d["name"].lower():
                metric_key = "operational.cash_conversion_cycle"

            ranked_drivers.append({
                "type": "drag",
                "metric": metric_key,
                "points": -abs(int(d["points"].replace("-", "").replace(" pts", ""))) if isinstance(d.get("points"), str) and d["points"].startswith("-") else -1,
                "detail": d["name"],
                "sub_metric_data": {
                    "margin_pct": margin_pct,
                    "quick_ratio": quick_ratio,
                    "inventory_turns": inventory_turns,
                    "ccc_days": ccc_days,
                    "trend_3mo": net_trend_3mo,
                }
            })

                
        # 6. Active Health Alerts (based on real thresholds)
        active_alerts = []

        if runway_months is not None and runway_months < 3:
            active_alerts.append({
                "alert_id": "low_runway_critical",
                "type": "critical",
                "description": f"Cash runway has fallen to {runway_months:.1f} months, creating elevated financial pressure if expenses remain unchanged.",
                "urgency_context": "Liquidity pressure may worsen quickly if expenses continue at the current pace.",
                "recommended_action": "Review operating expenses and cash preservation actions immediately."
            })

        elif runway_months is not None and runway_months < 6:
            active_alerts.append({
                "alert_id": "low_runway_warning",
                "type": "warning",
                "description": f"Cash runway is currently {runway_months:.1f} months, limiting financial flexibility if revenue slows or costs increase.",
                "urgency_context": "Reduced runway may limit flexibility during slower revenue periods.",
                "recommended_action": "Monitor cash flow weekly and identify controllable expense reductions."
            })

        if margin_pct is not None and margin_pct < 0.05:
            active_alerts.append({
                "alert_id": "low_margin_critical",
                "type": "critical",
                "description": f"Net margin has fallen to {margin_pct*100:.1f}%, leaving less room to absorb unexpected costs or revenue swings.",
                "urgency_context": "Sustained low profitability may weaken long-term financial stability.",
                "recommended_action": "Review pricing, operating costs, and low-margin activities immediately."
            })

        elif margin_pct is not None and margin_pct < 0.10:
            active_alerts.append({
                "alert_id": "low_margin_warning",
                "type": "warning",
                "description": f"Net margin is currently {margin_pct*100:.1f}%, which may reduce profitability cushion if operating costs rise.",
                "urgency_context": "Margin compression may reduce available cash flexibility over time.",
                "recommended_action": "Review expense trends and improve operational efficiency this month."
            })

        if quick_ratio is not None and quick_ratio < 1.0:
            active_alerts.append({
                "alert_id": "liquidity_warning",
                "type": "warning",
                "description": f"Liquidity is becoming tight. Quick ratio is {quick_ratio:.2f}, which may make short-term obligations harder to cover.",
                "urgency_context": "Short-term obligations may become harder to manage if cash inflows slow.",
                "recommended_action": "Prioritize receivables collection and preserve short-term liquidity."
            })

        if burn_rate_monthly is not None and burn_rate_monthly > revenue_mtd:
            active_alerts.append({
                "alert_id": "burn_rate_critical",
                "type": "critical",
                "description": "Monthly cash outflows are currently exceeding incoming revenue, which may reduce financial flexibility if sustained.",
                "urgency_context": "Sustained negative cash flow may reduce runway faster than expected.",
                "recommended_action": "Review recurring expenses and improve near-term cash inflows immediately."
            })

        if active_alerts is None:
            active_alerts = []
                
        # 7. Calculate AI Confidence based on data availability
        available_metrics = [
            margin_pct, runway_months, quick_ratio, current_ratio,
            inventory_turns, ccc_days, cash_flow_mtd, burn_rate_monthly
        ]
        available_count = sum(1 for m in available_metrics if m is not None)
        total_metrics = len(available_metrics)
        confidence_pct = int((available_count / total_metrics) * 100)

        if confidence_pct >= 80:
            confidence_label = "High data completeness"
        elif confidence_pct >= 60:
            confidence_label = "Moderate data completeness"
        else:
            confidence_label = "Limited data completeness"

        ai_confidence = f"{confidence_pct}%"
        ai_confidence_details = confidence_label


        business_health = {
            "Financial Health": {
                "score": fin_health_score,
                "summary": fin_summary,
                "label": fin_label,
            },
            "Operational Health": {
                "score": ops_score,
                "summary": ops_summary,
                "label": ops_label,
            },
            "Customer Health": {
                "score": cust_score,
                "summary": cust_summary,
                "label": cust_label,
            },
            "Risk Exposure": {
                "score": risk_score,
                "summary": risk_summary,
                "label": risk_label,
            },
            "Growth Momentum": {
                "score": growth_score,
                "summary": growth_summary,
                "label": growth_label,
            }
        }

        missing_categories = []

        if fin_health_score is None:
            missing_categories.append("financial")

        if ops_score is None:
            missing_categories.append("operational")

        if cust_score is None:
            missing_categories.append("customer")

        if risk_score is None:
            missing_categories.append("risk")

        if growth_score is None:
            missing_categories.append("growth")

        business_health_ai = await orchestrator_service.render_business_health({
            "intent": "render_business_health",
            "today_date": datetime.utcnow().date().isoformat(),
            "company_id": user_id,

            "user_id": user_id,

            "profile": {
                "owner_goals": [],
                "owner_priorities": [],
            },

            "overall": {
                "score": overall_score,
                "label": overall_label,
                "prior_score": None,
                "peer_avg": None,
                "trend_direction": "stable",
                "months_trending": 0,
                "period_high": None,
                "period_low": None,
                "crossed_peer_avg": False,
                "crossed_peer_avg_month": None,
                "ai_confidence": confidence_pct / 100,
                "data_completeness": confidence_pct,
                "incomplete_data": confidence_pct < 80,
            },

            "categories": {
                "financial": {
                    "score": fin_health_score,
                    "label": fin_label,
                    "prior_score": None,
                    "peer_avg": None,
                    "trend_direction": "stable",
                    "months_trending": 0,
                    "period_high": None,
                    "period_low": None,
                    "crossed_peer_avg": False,
                    "crossed_peer_avg_month": None,
                    "sub_metrics": [],
                    "missing": [] if fin_health_score is not None else ["financial_data"],
                },

                "operational": {
                    "score": ops_score,
                    "label": ops_label,
                    "prior_score": None,
                    "peer_avg": None,
                    "trend_direction": "stable",
                    "months_trending": 0,
                    "period_high": None,
                    "period_low": None,
                    "crossed_peer_avg": False,
                    "crossed_peer_avg_month": None,
                    "sub_metrics": [],
                    "missing": [] if ops_score is not None else ["operational_data"],
                },

                "customer": {
                    "score": cust_score,
                    "label": cust_label,
                    "prior_score": None,
                    "peer_avg": None,
                    "trend_direction": "stable",
                    "months_trending": 0,
                    "period_high": None,
                    "period_low": None,
                    "crossed_peer_avg": False,
                    "crossed_peer_avg_month": None,
                    "sub_metrics": [],
                    "missing": [] if cust_score is not None else ["customer_data"],
                },

                "risk": {
                    "score": risk_score,
                    "label": risk_label,
                    "prior_score": None,
                    "peer_avg": None,
                    "trend_direction": "stable",
                    "months_trending": 0,
                    "period_high": None,
                    "period_low": None,
                    "crossed_peer_avg": False,
                    "crossed_peer_avg_month": None,
                    "sub_metrics": [],
                    "missing": [] if risk_score is not None else ["risk_data"],
                },

                "growth": {
                    "score": growth_score,
                    "label": growth_label,
                    "prior_score": None,
                    "peer_avg": None,
                    "trend_direction": "stable",
                    "months_trending": 0,
                    "period_high": None,
                    "period_low": None,
                    "crossed_peer_avg": False,
                    "crossed_peer_avg_month": None,
                    "sub_metrics": [],
                    "missing": [] if growth_score is not None else ["growth_data"],
                },
            },

            "ranked_drivers": ranked_drivers,

            "detail_fields": {
                "revenue_by_customer": [],
                "overdue_invoices": [],
                "expense_by_vendor": [],
                "top_client_detail": {
                    "name": None,
                    "share": None,
                    "prior_share": None,
                    "trend": None,
                },
                "revenue_by_product": [],
            },

            "prior_period_snapshot": {
                "overall_score": None,
                "financial_score": None,
                "operational_score": None,
                "customer_score": None,
                "risk_score": None,
                "growth_score": None,
            },

            "signals": {
                "hard": active_alerts,
                "soft": priority_watch_areas,
                "stable": ranked_drivers,
            },

            "benchmarks": {
                "peer_pool": {},
                "metrics": [],
            },

            "data_coverage": {
                "connectors": {
                    "qbo": "connected",
                    "pos": "missing",
                    "reviews": "missing",
                },
                "missing_categories": missing_categories,
            },

            "priority_watch_areas": priority_watch_areas,

            "real_data_metrics": {
                "margin_pct": margin_pct,
                "runway_months": runway_months,
                "quick_ratio": quick_ratio,
                "inventory_turns": inventory_turns,
                "ccc_days": ccc_days,
                "trend_3mo": net_trend_3mo,
            }
        })

        drivers_display = business_health_ai.get(
            "drivers_display",
            {
                "positive": [],
                "drags": []
            }
        )

        ai_summary = business_health_ai.get(
            "ai_summary",
            "Business health insights generated successfully."
        )
        
        # 8.a Data Gap Guidance
        data_gap_guidance = []

        if margin_pct is None:
            data_gap_guidance.append(
                "Profitability metrics are incomplete. Ensure income and expense accounts are fully synced from QuickBooks."
            )

        if inventory_turns is None:
            data_gap_guidance.append(
                "Inventory efficiency metrics are unavailable because inventory tracking data is missing."
            )

        if runway_months is None:
            data_gap_guidance.append(
                "Cash runway could not be calculated because expense or cash balance data is incomplete."
            )

        if ccc_days is None:
            data_gap_guidance.append(
                "Cash conversion cycle metrics require receivables, payables, and inventory data."
            )
        # 9. Construct Response (NO dummy data)
        response = {
            "Business Health": {
                "Overall Business Health": {
                    "score": overall_score,
                    "label": overall_label,
                    "trend": "↑" if net_trend_3mo == "positive" else ("↓" if net_trend_3mo == "negative" else "→"),
                    "peer_avg": None,  # We don't have peer data
                    "yours": overall_score,
                    "time_period": range,
                    "data_completeness": confidence_pct,
                    "incomplete_data": confidence_pct < 80,
                },

                "Financial Health": {
                    "score": fin_health_score,
                    "summary": fin_summary,
                    "label": fin_label,
                    "missing_data_notice": (
                        None if fin_health_score is not None
                        else "Connect financial data sources to calculate this score."
                    )
                },
                "Operational Health": {
                    "score": ops_score,
                    "summary": ops_summary,
                    "label": ops_label,
                    "missing_data_notice": (
                        None if ops_score is not None
                        else "Connect operational and inventory data sources to calculate this score."
                    )
                },
                "Customer Health": {
                    "score": cust_score,
                    "summary": cust_summary,
                    "label": cust_label,
                    "missing_data_notice": (
                        "Connect customer and review data sources to calculate this score."
                    )
                },
                "Risk Exposure": {
                    "score": risk_score,
                    "summary": risk_summary,
                    "label": risk_label,
                    "missing_data_notice": risk_missing_notice
                },
                "Growth Momentum": {
                    "score": growth_score,
                    "summary": growth_summary,
                    "label": growth_label,
                    "missing_data_notice": (
                        None if growth_score is not None
                        else "Connect historical revenue data to calculate this score."
                    )
                },
            },
            "AI Confidence Index": ai_confidence,
            "AI Confidence Details": ai_confidence_details,
            "Overview Dashboard": {
                "AI summary": ai_summary,
                "AI diagnosis": f"Score is {overall_score} ({overall_label})." if overall_score is not None else "Insufficient data"
            },
            "Drivers": {
                "Top Positive Drivers": positive_drivers if positive_drivers else None,
                "Top Drags": drags if drags else None
            },
            "ranked_drivers": ranked_drivers,
            "drivers_display": drivers_display,
            "Priority Watch Areas": priority_watch_areas if priority_watch_areas else None,
            "Watch Area Explanation": watch_area_explanation if watch_area_explanation else None,
            "Active Health Alerts": active_alerts,
            "Quadrants": {
                "Financial Health": {
                    "score": fin_health_score,
                    "summary": fin_summary,
                    "label": fin_label,
                    "missing_data_notice": (
                        None if fin_health_score is not None
                        else "Connect financial data sources to calculate this score."
                    )
                },
                "Operational Health": {
                    "score": ops_score,
                    "summary": ops_summary,
                    "label": ops_label,
                    "missing_data_notice": (
                        None if ops_score is not None
                        else "Connect operational and inventory data sources to calculate this score."
                    )
                },
                "Customer Health": {
                    "score": cust_score,
                    "summary": cust_summary,
                    "label": cust_label,
                    "missing_data_notice": (
                        "Connect customer and review data sources to calculate this score."
                    )
                },
                "Risk Exposure": {
                    "score": risk_score,
                    "summary": risk_summary,
                    "label": risk_label,
                    "missing_data_notice": risk_missing_notice
                },
                "Growth Momentum": {
                    "score": growth_score,
                    "summary": growth_summary,
                    "label": growth_label,
                    "missing_data_notice": (
                        None if growth_score is not None
                        else "Connect historical revenue data to calculate this score."
                    )
                }
            },

            "Data Gap Guidance": data_gap_guidance if data_gap_guidance else None,
            
            "Real Data Metrics": {
                "revenue_mtd": revenue_mtd,
                "net_margin_pct": margin_pct,
                "gross_margin_pct": gross_margin_pct,
                "cash": cash,
                "runway_months": runway_months,
                "quick_ratio": quick_ratio,
                "current_ratio": current_ratio,
                "inventory_turns": inventory_turns,
                "ccc_days": ccc_days,
                "cash_flow_mtd": cash_flow_mtd,
                "burn_rate_monthly": burn_rate_monthly,
                "trend_3mo": net_trend_3mo
            }
        }
        
        # Remove None values from response
        response = {k: v for k, v in response.items() if v is not None}

        # Log successful insights view
        await feature_usage_service.log_usage(user_id, "insights")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(response),
        )

    except Exception as exc:
        # raise HTTPException(
        #     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #     detail=f"Failed to generate health report: {str(exc)}",
        # )
        traceback.print_exc()
        raise

@router.post("/refresh")
async def refresh_business_health(
    current_user: dict = Depends(get_current_user),
):
    """
    Manually refresh Business Health data.
    Forces latest QuickBooks pull and regenerates health metrics.
    """
    try:
        user_id = current_user["id"]

        refresh_result = await orchestrator_service.refresh_all_business_data(
            user_id=user_id
        )

        return refresh_result

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh Business Health: {str(exc)}",
        )