from typing import List, Any, Optional, Dict
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.routes.auth.auth import get_current_user
from app.services.claude_service import claude_service
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.services.feature_usage_service import feature_usage_service
from app.services.orchestrator_service import OrchestratorService
from datetime import datetime
from app.services.business_health_engine_service import business_health_engine_service
from app.services.business_health_snapshot_service import business_health_snapshot_service
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

    try:
        prompt = (
            "You are a concise business advisor. "
            
            "Given prioritized watch areas for a small business, return exactly 3 short bullet points: 1) what it means, 2) where to focus, 3) what to do next. "
            "Use minimal words and no paragraph text. "
            "Input watch areas:\n"
            + "\n".join(f"- {area}" for area in watch_areas)
            + "\nOutput only plain text, with bullets in this format: '- ...'."
        )
        text = await claude_service.text_completion(
            system_prompt="You are a friendly business advisor.",
            user_content=prompt,
            temperature=0.2,
            max_tokens=220,
        )

        text = text.strip()
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



def _normalize_demo_business_health_v6(raw_bh: dict, login_label: str = "demo-restaurant") -> dict:
    """Normalize legacy demo business health objects to V6 rich schema."""
    overall_score = raw_bh.get("overall_score", 80)
    dims = raw_bh.get("dimensions", {})
    
    fin_score = dims.get("liquidity", {}).get("score", 82)
    ops_score = dims.get("efficiency", {}).get("score", 74)
    cust_score = dims.get("customer", {}).get("score", 79)
    risk_score = dims.get("resilience", {}).get("score", 85)
    growth_score = dims.get("growth", {}).get("score", 81)
    
    return {
        "overall": {
            "score": overall_score,
            "label": "above_average" if overall_score >= 75 else "at_average",
            "prior_score": overall_score - 4,
            "peer_avg": 71,
            "ai_confidence": 0.88,
            "data_completeness": 88,
            "incomplete_data": False,
            "as_of": datetime.utcnow().date().isoformat()
        },
        "categories": {
            "financial": {"score": fin_score, "label": "above_average", "prior_score": fin_score - 3, "peer_avg": 72, "missing": []},
            "operational": {"score": ops_score, "label": "at_average", "prior_score": ops_score - 2, "peer_avg": 70, "missing": []},
            "customer": {"score": cust_score, "label": "above_average", "prior_score": cust_score - 1, "peer_avg": 75, "missing": []},
            "risk": {"score": risk_score, "label": "top_tier", "prior_score": risk_score, "peer_avg": 68, "missing": []},
            "growth": {"score": growth_score, "label": "above_average", "prior_score": growth_score - 5, "peer_avg": 69, "missing": []}
        },
        "benchmarks": {
            "peer_pool": "Regional Small Business Benchmark Pool",
            "peer_avg": 71
        },
        "ai_summary": "Core operating health is resilient. Cash flow trajectory is steady with solid margin retention.",
        "drivers_display": {
            "positives": [
                {
                    "headline": "Strong retail & service attach rate",
                    "description": "Cross-category attach rate increased by 8% over prior quarter.",
                    "recommended_action": "Expand successful promotional bundles."
                }
            ],
            "drags": [
                {
                    "headline": "Receivables collection lag",
                    "description": "Invoice collection velocity dropped 4 days below benchmark.",
                    "recommended_action": "Enable 14-day early pay incentive terms."
                }
            ]
        },
        "watch_areas": [
            {
                "title": "Peak Period Staffing & Capacity Gap",
                "description": "Weekend demand utilization reached 92%, causing minor customer wait times.",
                "possible_causes": [{"cause": "Staffing schedule bottleneck", "evidence": "92% peak utilization"}],
                "recommended_action": "Adjust weekend shift overlaps by 1 hour.",
                "owner_confirmation_prompt": "Confirm if weekend wait times exceed 15 minutes?",
                "learning_id": "learn_capacity_01"
            }
        ],
        "active_alerts": [
            {
                "description": "Uncollected receivables extending runway pressure by $2,400",
                "urgency_context": "Why now: Overdue invoices doubled this month.",
                "recommended_action": "Send automated email reminders for 30+ day past-due invoices."
            }
        ],
        "data_coverage_note": "QuickBooks & POS synced 2h ago"
    }


@router.get("/full")
async def get_business_health_full(
    range: str = Query("12m"),
    include_peers: bool = Query(True),
    include_breakdowns: bool = Query(True),
    current_user: dict = Depends(get_current_user),
):
    """
    Get comprehensive Business Health Scorecard V6.
    Returns Financial, Operational, Customer, Risk, and Growth health metrics.
    """
    try:
        user_id = current_user["id"]
        
        # Check if demo user
        from app.db import get_collection
        users_col = get_collection("users")
        user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
        
        if user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", "")):
            login_label = user_doc.get("login_label") or user_doc.get("username")
            if not login_label and user_doc.get("email"):
                login_label = user_doc.get("email").split("@")[0]
            
            from app.demo_data import get_demo_payload
            demo_payload = get_demo_payload(login_label or "demo-restaurant")
            if demo_payload and "business_health" in demo_payload:
                raw_bh = demo_payload["business_health"]
                if "overall" not in raw_bh:
                    v6_bh = _normalize_demo_business_health_v6(raw_bh, login_label)
                else:
                    v6_bh = raw_bh
                return JSONResponse(status_code=200, content={"success": True, "data": v6_bh, **v6_bh})

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
        if isinstance(financial_overview, dict):
            financial_overview.setdefault("Real Data Metrics", {
                "net_margin_pct": margin_pct,
                "runway_months": runway_months,
                "quick_ratio": quick_ratio,
                "inventory_turns": inventory_turns,
                "ccc_days": ccc_days,
                "trend_3mo": net_trend_3mo,
            })
        engine_result = await business_health_engine_service.generate_business_health(
            user_id=user_id,
            financial_overview=financial_overview or {}
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

        # 4.5 Ingest Storefront & Location learnings
        # Read-precedence rule (storefront/08 - Rule - Which Location Read Wins.md): a measured
        # storefront vitality read must win over the Classifier's geographic_context guess when
        # they conflict. Audited: this codebase's Classifier never emits a geographic_context /
        # foot-traffic prose field, and no other consumer (generate_watch_area_explanation below
        # only summarizes this already-built priority_watch_areas list) asserts a competing
        # location claim - so there is nothing here for the storefront read to be overridden by.
        # The rule is satisfied by construction; re-check this comment if a future Classifier
        # revision starts emitting a geographic_context claim into priority_watch_areas.
        try:
            from app.services.customer_memory_service import CustomerMemoryService
            memory_service = CustomerMemoryService()
            memories = await memory_service.get_memory_by_user(user_id=user_id, limit=100)
            
            for memory in memories:
                if memory.get("observation_type") == "pattern" and "storefront" in memory.get("tags", []):
                    supp_data = memory.get("supporting_data", {})
                    # Look at presentation flags
                    m1 = supp_data.get("module_1_presentation", {})
                    if isinstance(m1, dict):
                        fit_flags = m1.get("pass2_fit_flags", [])
                        for flag_obj in fit_flags:
                            if isinstance(flag_obj, dict):
                                title = flag_obj.get("flag", "Presentation mismatch detected")
                                basis = flag_obj.get("basis", "")
                                priority_watch_areas.append(f"{title}: {basis} (Ref: {memory['_id']})")
                                
                    # Look at location vitality
                    m2 = supp_data.get("module_2_vitality", {})
                    if isinstance(m2, dict):
                        overall = m2.get("overall", "moderate")
                        if overall in ["quiet", "quiet_for_context", "declining"]:
                            context_note = m2.get("context_note", "")
                            signals_summary = "; ".join([s.get("value", "") for s in m2.get("signals", []) if isinstance(s, dict)])
                            priority_watch_areas.append(f"Location Vitality is {overall.replace('_', ' ')}: {context_note}. Signals: {signals_summary} (Ref: {memory['_id']})")
        except Exception as e:
            print(f"[DEBUG] Error loading storefront learnings: {e}")

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

        try:
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
        except Exception as e:
            print(f"[WARN] Failed to render AI business health: {e}")
            business_health_ai = {}

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
        # Fetch prior snapshot from MongoDB for prior_score calculation
        prior_snapshot = await business_health_snapshot_service.get_prior_snapshot(user_id) if hasattr(business_health_snapshot_service, "get_prior_snapshot") else None
        prior_payload = (prior_snapshot.snapshot_payload if prior_snapshot and hasattr(prior_snapshot, "snapshot_payload") else {}) or {}
        prior_overall = prior_payload.get("overall", {}) or {}
        prior_categories = prior_payload.get("categories", {}) or {}

        prior_overall_score = prior_overall.get("score") if isinstance(prior_overall, dict) else None

        # Build Canonical Spec Data Contracts (LightSignal_BH_Tab_Developer_Spec_v1.md)
        canonical_overall = {
            "score": overall_score,
            "label": overall_label,
            "prior_score": prior_overall_score,
            "peer_avg": engine_result.get("overall", {}).get("peer_avg") if isinstance(engine_result.get("overall"), dict) else None,
            "ai_confidence": confidence_pct / 100.0,
            "data_completeness": confidence_pct,
            "incomplete_data": confidence_pct < 80,
            "as_of": datetime.utcnow().date().isoformat(),
        }

        canonical_categories = {
            "financial": {
                "score": fin_health_score,
                "label": fin_label,
                "prior_score": prior_categories.get("financial", {}).get("score") if isinstance(prior_categories.get("financial"), dict) else None,
                "peer_avg": None,
                "missing": [] if fin_health_score is not None else ["financial_data"],
            },
            "operational": {
                "score": ops_score,
                "label": ops_label,
                "prior_score": prior_categories.get("operational", {}).get("score") if isinstance(prior_categories.get("operational"), dict) else None,
                "peer_avg": None,
                "missing": [] if ops_score is not None else ["pos"],
            },
            "customer": {
                "score": cust_score,
                "label": cust_label,
                "prior_score": prior_categories.get("customer", {}).get("score") if isinstance(prior_categories.get("customer"), dict) else None,
                "peer_avg": None,
                "missing": ["reviews"],
            },
            "risk": {
                "score": risk_score,
                "label": risk_label,
                "prior_score": prior_categories.get("risk", {}).get("score") if isinstance(prior_categories.get("risk"), dict) else None,
                "peer_avg": None,
                "missing": [],
            },
            "growth": {
                "score": growth_score,
                "label": growth_label,
                "prior_score": prior_categories.get("growth", {}).get("score") if isinstance(prior_categories.get("growth"), dict) else None,
                "peer_avg": None,
                "missing": [] if growth_score is not None else ["historical_revenue"],
            },
        }

        canonical_benchmarks = {
            "peer_pool": "Regional Small Business Pool",
            "peer_avg": canonical_overall.get("peer_avg"),
        }

        # Calculate dynamic QuickBooks sync age from MongoDB
        from app.db import get_collection
        sync_time_str = "just now"
        try:
            qb_doc = await get_collection("quickbooks_tokens").find_one({"user_id": user_id})
            last_ts = (qb_doc.get("updated_at") or qb_doc.get("created_at")) if qb_doc else None
            if not last_ts:
                snap_doc = await get_collection("financial_overview_snapshots").find_one({"user_id": user_id})
                last_ts = snap_doc.get("created_at") if snap_doc else None
                
            if last_ts:
                if isinstance(last_ts, str):
                    last_ts = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                now = datetime.utcnow()
                diff_sec = (now - last_ts.replace(tzinfo=None)).total_seconds()
                if diff_sec < 60:
                    sync_time_str = "just now"
                elif diff_sec < 3600:
                    sync_time_str = f"{int(diff_sec // 60)}m ago"
                elif diff_sec < 86400:
                    sync_time_str = f"{int(diff_sec // 3600)}h ago"
                else:
                    sync_time_str = f"{int(diff_sec // 86400)}d ago"
        except Exception:
            sync_time_str = "recently"

        canonical_data_coverage_note = f"QuickBooks synced {sync_time_str}" if confidence_pct >= 80 else "Connect POS & Review data to sharpen Operational & Customer reads"

        canonical_watch_areas = []
        raw_watch_areas = business_health_ai.get("watch_areas", priority_watch_areas)
        if isinstance(raw_watch_areas, list):
            for wa in raw_watch_areas:
                if isinstance(wa, dict):
                    canonical_watch_areas.append({
                        "title": wa.get("title") or wa.get("area") or wa.get("name") or "Priority Watch Area",
                        "description": wa.get("description") or wa.get("summary") or "",
                        "possible_causes": wa.get("possible_causes", []),
                        "recommended_action": wa.get("recommended_action") or wa.get("action") or "",
                        "owner_confirmation_prompt": wa.get("owner_confirmation_prompt"),
                        "learning_id": wa.get("learning_id"),
                    })
                elif isinstance(wa, str):
                    canonical_watch_areas.append({
                        "title": wa,
                        "description": f"Review {wa.lower()} operating performance.",
                        "possible_causes": [],
                        "recommended_action": f"Put a corrective action in place for {wa.lower()} this week.",
                        "owner_confirmation_prompt": None,
                        "learning_id": None,
                    })

        canonical_active_alerts = []
        raw_active_alerts = business_health_ai.get("active_alerts", active_alerts)
        if isinstance(raw_active_alerts, list):
            for alert in raw_active_alerts:
                if isinstance(alert, dict):
                    canonical_active_alerts.append({
                        "description": alert.get("description") or alert.get("headline") or "",
                        "urgency_context": alert.get("urgency_context") or alert.get("why_now") or "Immediate action required.",
                        "recommended_action": alert.get("recommended_action") or alert.get("action") or "",
                    })
                elif isinstance(alert, str):
                    canonical_active_alerts.append({
                        "description": alert,
                        "urgency_context": "Requires owner review this week.",
                        "recommended_action": "Review metric details and take action.",
                    })

        response = {
            "success": True,
            "data": {
                "overall": canonical_overall,
                "categories": canonical_categories,
                "benchmarks": canonical_benchmarks,
                "ai_summary": ai_summary,
                "drivers_display": drivers_display,
                "watch_areas": canonical_watch_areas,
                "active_alerts": canonical_active_alerts,
                "data_coverage_note": canonical_data_coverage_note,
            },
            # Backwards compatibility wrappers
            "overall": canonical_overall,
            "categories": canonical_categories,
            "benchmarks": canonical_benchmarks,
            "ai_summary": ai_summary,
            "drivers_display": drivers_display,
            "watch_areas": canonical_watch_areas,
            "active_alerts": canonical_active_alerts,
            "data_coverage_note": canonical_data_coverage_note,
        }

        # Log successful insights view
        await feature_usage_service.log_usage(user_id, "insights")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(response),
        )

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate health report: {str(exc)}",
        )


@router.get("/snapshots")
async def list_business_health_snapshots(
    limit: int = Query(20, ge=1, le=100),
    current_user: Any = Depends(get_current_user),
):
    """
    Returns list of historical Business Health snapshots for the snapshot dropdown menu.
    """
    if isinstance(current_user, dict):
        user_id = current_user.get("id") or current_user.get("_id")
        email = current_user.get("email", "")
    else:
        user_id = str(current_user)
        email = ""

    is_demo_flag = (isinstance(current_user, dict) and current_user.get("is_demo")) or (email.startswith("demo-") and "@lightsignal.app" in email)
    if not is_demo_flag:
        users_col = get_collection("users")
        user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
        is_demo_flag = user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", ""))
        login_label = user_doc.get("login_label") or user_doc.get("username") or (user_doc.get("email", "").split("@")[0] if user_doc.get("email") else "demo-restaurant")
    else:
        login_label = current_user.get("login_label") or current_user.get("username") or (email.split("@")[0] if email else "demo-restaurant")

    # Demo users: return demo snapshot dropdown list
    if is_demo_flag:
        from app.demo_data import get_demo_payload
        demo_payload = get_demo_payload(login_label or "demo-restaurant")
        raw_bh = (demo_payload.get("business_health") if demo_payload else {}) or {}
        current_score = raw_bh.get("overall_score", 82)
        now = datetime.utcnow()
        items = [
            {
                "snapshot_id": "snap_demo_curr",
                "score": current_score,
                "label": "Above Average",
                "created_at": now.isoformat(),
            },
            {
                "snapshot_id": "snap_demo_prev1",
                "score": current_score - 4,
                "label": "Above Average",
                "created_at": (now - timedelta(days=30)).isoformat(),
            },
            {
                "snapshot_id": "snap_demo_prev2",
                "score": current_score - 7,
                "label": "At Average",
                "created_at": (now - timedelta(days=60)).isoformat(),
            }
        ]
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": items,
            })
        )

    # Normal users: fetch from MongoDB
    col = get_collection("business_health_snapshots")
    docs = await col.find({"user_id": user_id}).sort("created_at", -1).limit(limit).to_list(length=limit)
    
    items = []
    for doc in docs:
        created = doc.get("created_at")
        payload = doc.get("snapshot_payload") if isinstance(doc.get("snapshot_payload"), dict) else {}
        overall = payload.get("overall") if isinstance(payload.get("overall"), dict) else {}
        items.append({
            "snapshot_id": str(doc.get("_id")),
            "score": doc.get("overall_score") or overall.get("score"),
            "label": doc.get("overall_label") or overall.get("label"),
            "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created or ""),
        })

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": items,
        })
    )


@router.get("/snapshots/{snapshot_id}")
async def get_business_health_snapshot_detail(
    snapshot_id: str,
    current_user: Any = Depends(get_current_user),
):
    """
    Returns detailed snapshot payload for Compare Mode with all 5 canonical categories.
    """
    from bson import ObjectId

    if isinstance(current_user, dict):
        user_id = current_user.get("id") or current_user.get("_id")
        email = current_user.get("email", "")
    else:
        user_id = str(current_user)
        email = ""

    is_demo_flag = (isinstance(current_user, dict) and current_user.get("is_demo")) or (email.startswith("demo-") and "@lightsignal.app" in email)
    if not is_demo_flag:
        users_col = get_collection("users")
        user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
        is_demo_flag = user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", ""))
        login_label = user_doc.get("login_label") or user_doc.get("username") or (user_doc.get("email", "").split("@")[0] if user_doc.get("email") else "demo-restaurant")
    else:
        login_label = current_user.get("login_label") or current_user.get("username") or (email.split("@")[0] if email else "demo-restaurant")

    # Demo users: return spec-compliant demo snapshot payload
    if is_demo_flag:
        from app.demo_data import get_demo_payload
        demo_payload = get_demo_payload(login_label or "demo-restaurant")
        raw_bh = (demo_payload.get("business_health") if demo_payload else {}) or {}
        if "overall" not in raw_bh:
            v6_bh = _normalize_demo_business_health_v6(raw_bh, login_label)
        else:
            v6_bh = raw_bh

        base_overall = v6_bh.get("overall", {})
        prior_score = base_overall.get("score", 82) - 4
        prior_overall = {
            "score": prior_score,
            "label": "above_average" if prior_score >= 75 else "at_average",
            "peer_avg": base_overall.get("peer_avg", 71),
            "ai_confidence": 0.86,
            "data_completeness": 86,
            "incomplete_data": False,
            "as_of": (datetime.utcnow() - timedelta(days=30)).date().isoformat()
        }

        prior_categories = {
            "financial": {"score": 79, "label": "above_average", "prior_score": None, "peer_avg": 72, "missing": []},
            "operational": {"score": 72, "label": "at_average", "prior_score": None, "peer_avg": 70, "missing": []},
            "customer": {"score": 78, "label": "above_average", "prior_score": None, "peer_avg": 75, "missing": []},
            "risk": {"score": 85, "label": "top_tier", "prior_score": None, "peer_avg": 68, "missing": []},
            "growth": {"score": 76, "label": "above_average", "prior_score": None, "peer_avg": 69, "missing": []},
            "financial_health": {"score": 79, "label": "above_average", "prior_score": None, "peer_avg": 72, "missing": []},
            "operational_health": {"score": 72, "label": "at_average", "prior_score": None, "peer_avg": 70, "missing": []},
            "customer_health": {"score": 78, "label": "above_average", "prior_score": None, "peer_avg": 75, "missing": []},
            "risk_health": {"score": 85, "label": "top_tier", "prior_score": None, "peer_avg": 68, "missing": []},
            "growth_health": {"score": 76, "label": "above_average", "prior_score": None, "peer_avg": 69, "missing": []},
        }

        snapshot_res = {
            **v6_bh,
            "overall": prior_overall,
            "categories": prior_categories,
            "financial_health": prior_categories["financial"],
            "operational_health": prior_categories["operational"],
            "customer_health": prior_categories["customer"],
            "risk_health": prior_categories["risk"],
            "growth_health": prior_categories["growth"],
            "ai_summary": "Prior operating snapshot reflected solid margin retention and steady order velocity.",
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": snapshot_res,
                "overall": prior_overall,
                "categories": prior_categories,
                "financial_health": prior_categories["financial"],
                "operational_health": prior_categories["operational"],
                "customer_health": prior_categories["customer"],
                "risk_health": prior_categories["risk"],
                "growth_health": prior_categories["growth"],
                "active_alerts": v6_bh.get("active_alerts", []),
                "watch_areas": v6_bh.get("watch_areas", []),
                "drivers_display": v6_bh.get("drivers_display", []),
                "ai_summary": snapshot_res["ai_summary"],
            })
        )

    # Normal users: fetch from DB
    col = get_collection("business_health_snapshots")
    doc = None

    if snapshot_id and snapshot_id.lower() != "latest":
        try:
            if ObjectId.is_valid(snapshot_id):
                doc = await col.find_one({"user_id": user_id, "$or": [{"_id": snapshot_id}, {"_id": ObjectId(snapshot_id)}]})
            else:
                doc = await col.find_one({"user_id": user_id, "_id": snapshot_id})
        except Exception:
            doc = None

    if not doc:
        try:
            # Fallback to the MOST RECENT snapshot (sort by created_at DESC)
            doc = await col.find_one({"user_id": user_id}, sort=[("created_at", -1)])
        except Exception as db_err:
            print(f"[get_business_health_snapshot_detail] DB fallback error: {db_err}")
            doc = None
    
    if not doc:
        default_payload = {
            "overall": {"score": 75, "label": "Healthy", "ai_confidence": 0.85},
            "categories": {
                "financial": {"score": 75, "label": "Good", "missing": []},
                "operational": {"score": 70, "label": "Stable", "missing": []},
                "customer": {"score": 76, "label": "Good", "missing": []},
                "risk": {"score": 80, "label": "Low Risk", "missing": []},
                "growth": {"score": 72, "label": "Growing", "missing": []},
                "financial_health": {"score": 75, "label": "Good"},
                "operational_health": {"score": 70, "label": "Stable"},
                "customer_health": {"score": 76, "label": "Good"},
                "risk_health": {"score": 80, "label": "Low Risk"},
                "growth_health": {"score": 72, "label": "Growing"}
            },
            "financial_health": {"score": 75, "label": "Good"},
            "operational_health": {"score": 70, "label": "Stable"},
            "customer_health": {"score": 76, "label": "Good"},
            "risk_health": {"score": 80, "label": "Low Risk"},
            "growth_health": {"score": 72, "label": "Growing"},
            "active_alerts": [],
            "watch_areas": [],
            "drivers_display": [],
            "ai_summary": "Initial baseline snapshot.",
            "benchmarks": {"peer_pool": "Regional Small Business Pool", "peer_avg": 70},
            "data_coverage_note": None
        }
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": default_payload,
                "overall": default_payload["overall"],
                "categories": default_payload["categories"],
                "financial_health": default_payload["financial_health"],
                "operational_health": default_payload["operational_health"],
                "customer_health": default_payload["customer_health"],
                "risk_health": default_payload["risk_health"],
                "growth_health": default_payload["growth_health"],
                "active_alerts": [],
                "watch_areas": [],
                "drivers_display": [],
            })
        )
        
    payload = doc.get("snapshot_payload") if isinstance(doc.get("snapshot_payload"), dict) else doc
    if not isinstance(payload, dict):
        payload = {}

    # Standardize canonical shape mapping
    overall = payload.get("overall") or {
        "score": doc.get("overall_score"),
        "label": doc.get("overall_label"),
    }
    
    raw_cats = payload.get("categories") if isinstance(payload.get("categories"), dict) else {}

    fin_health = payload.get("financial_health") or raw_cats.get("financial_health") or raw_cats.get("financial")
    op_health = payload.get("operational_health") or raw_cats.get("operational_health") or raw_cats.get("operational")
    cust_health = payload.get("customer_health") or raw_cats.get("customer_health") or raw_cats.get("customer")
    risk_health = payload.get("risk_health") or raw_cats.get("risk_health") or raw_cats.get("risk")
    growth_health = payload.get("growth_health") or raw_cats.get("growth_health") or raw_cats.get("growth")

    if not isinstance(fin_health, dict):
        fin_health = {"score": None, "label": "missing_data", "missing": ["financial"]}
    if not isinstance(op_health, dict):
        op_health = {"score": None, "label": "missing_data", "missing": ["operational", "pos"]}
    if not isinstance(cust_health, dict):
        cust_health = {"score": None, "label": "missing_data", "missing": ["customer", "reviews"]}
    if not isinstance(risk_health, dict):
        risk_health = {"score": None, "label": "missing_data", "missing": ["risk"]}
    if not isinstance(growth_health, dict):
        growth_health = {"score": None, "label": "missing_data", "missing": ["growth"]}

    categories = {
        "financial": fin_health,
        "operational": op_health,
        "customer": cust_health,
        "risk": risk_health,
        "growth": growth_health,
        "financial_health": fin_health,
        "operational_health": op_health,
        "customer_health": cust_health,
        "risk_health": risk_health,
        "growth_health": growth_health,
    }

    active_alerts = payload.get("active_alerts") or payload.get("active_health_alerts") or []
    watch_areas = payload.get("watch_areas") or payload.get("priority_watch_areas") or []
    drivers_display = payload.get("drivers_display") or payload.get("score_drivers") or []

    response_data = {
        "overall": overall,
        "categories": categories,
        "financial_health": fin_health,
        "operational_health": op_health,
        "customer_health": cust_health,
        "risk_health": risk_health,
        "growth_health": growth_health,
        "active_alerts": active_alerts,
        "watch_areas": watch_areas,
        "drivers_display": drivers_display,
        "ai_summary": payload.get("ai_summary") or doc.get("ai_summary"),
        "benchmarks": payload.get("benchmarks", {}),
        "data_coverage_note": payload.get("data_coverage_note"),
        **payload
    }

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": response_data,
            # Top-level fallbacks for backwards compatibility
            "overall": overall,
            "categories": categories,
            "financial_health": fin_health,
            "operational_health": op_health,
            "customer_health": cust_health,
            "risk_health": risk_health,
            "growth_health": growth_health,
            "active_alerts": active_alerts,
            "watch_areas": watch_areas,
            "drivers_display": drivers_display,
        })
    )


class WatchAreaResponseRequest(BaseModel if 'BaseModel' in globals() else object):
    action: str  # "confirm" | "correct" | "dismiss"
    correction_text: Optional[str] = None


@router.post("/watch-areas/{learning_id}/respond")
async def respond_to_location_watch_area(
    learning_id: str,
    action: str = Query(..., description="confirm | correct | dismiss"),
    correction_text: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Storefront & Location Owner-Check endpoint (§4.3 Addendum).
    Persists owner Confirm, Correct, or Dismiss response into business record.
    """
    user_id = current_user["id"]
    from app.db import get_collection
    col = get_collection("location_owner_responses")
    
    response_doc = {
        "user_id": user_id,
        "learning_id": learning_id,
        "action": action,
        "correction_text": correction_text,
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    await col.update_one(
        {"user_id": user_id, "learning_id": learning_id},
        {"$set": response_doc},
        upsert=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "message": f"Watch area response '{action}' saved to business record",
            "data": response_doc,
        })
    )


@router.post("/refresh")
async def refresh_business_health(
    current_user: dict = Depends(get_current_user),
):
    """
    Manually refresh Business Health data.
    Forces latest QuickBooks pull and regenerates health metrics.
    """
    user_id = current_user["id"]
    from app.services.cost_guardrail_service import cost_guardrail_service
    allowed, reason = await cost_guardrail_service.check_and_reserve(user_id, "manual_refresh")
    if not allowed:
        detail_msg = (
            "You've reached today's limit for this action. It resets at midnight."
            if reason == "surface_cap" else
            "You've reached today's usage limit for your account. It resets at midnight. Contact support if you need more."
        )
        raise HTTPException(status_code=429, detail=detail_msg)

    try:
        try:
            refresh_result = await orchestrator_service.refresh_all_business_data(
                user_id=user_id
            )
        except Exception as e:
            await cost_guardrail_service.refund_reserve(user_id, "manual_refresh")
            raise e

        return refresh_result

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh Business Health: {str(exc)}",
        )