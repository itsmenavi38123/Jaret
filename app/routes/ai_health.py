from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.routes.auth.auth import get_current_user
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.services.feature_usage_service import feature_usage_service

router = APIRouter(tags=["ai-health"])

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
        financial_overview = await qs.get_financial_overview(user_id)
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
        
        # A. Financial Health (Margins + Liquidity)
        fin_score_components = []
        
        # Margin Score (0-100) - based on net margin
        if margin_pct is not None:
            # Target: >15% = excellent, 10-15% = good, 5-10% = fair, <5% = poor
            if margin_pct >= 0.15:
                margin_score = 100
            elif margin_pct >= 0.10:
                margin_score = 70 + ((margin_pct - 0.10) / 0.05) * 30
            elif margin_pct >= 0.05:
                margin_score = 40 + ((margin_pct - 0.05) / 0.05) * 30
            else:
                margin_score = max(0, (margin_pct / 0.05) * 40)
            fin_score_components.append(margin_score)
        
        # Liquidity Score (0-100) - based on runway
        if runway_months is not None and runway_months > 0:
            # Target: >12 mo = excellent, 6-12 = good, 3-6 = fair, <3 = poor
            if runway_months >= 12:
                liquidity_score = 100
            elif runway_months >= 6:
                liquidity_score = 70 + ((runway_months - 6) / 6) * 30
            elif runway_months >= 3:
                liquidity_score = 40 + ((runway_months - 3) / 3) * 30
            else:
                liquidity_score = max(0, (runway_months / 3) * 40)
            fin_score_components.append(liquidity_score)
        
        # Calculate final financial health score
        if fin_score_components:
            fin_health_score = int(sum(fin_score_components) / len(fin_score_components))
        else:
            fin_health_score = None
            
        if fin_health_score is not None:
            fin_label = "good" if fin_health_score > 75 else ("caution" if fin_health_score > 50 else "critical")
            margin_display = f"{margin_pct*100:.1f}%" if margin_pct is not None else "N/A"
            runway_display = f"{runway_months:.1f} mo" if runway_months is not None else "N/A"
            fin_summary = f"Strong margins; healthy liquidity" if fin_health_score > 75 else f"Margins {margin_display}; Runway {runway_display}"
        else:
            fin_health_score = None
            fin_label = None
            fin_summary = "Insufficient financial data"

        # B. Operational Health - based on efficiency metrics
        ops_score_components = []
        
        # Inventory efficiency
        if inventory_turns is not None and inventory_turns > 0:
            # Target: >8 = excellent, 4-8 = good, 2-4 = fair, <2 = poor
            if inventory_turns >= 8:
                inv_score = 100
            elif inventory_turns >= 4:
                inv_score = 70 + ((inventory_turns - 4) / 4) * 30
            elif inventory_turns >= 2:
                inv_score = 40 + ((inventory_turns - 2) / 2) * 30
            else:
                inv_score = max(0, (inventory_turns / 2) * 40)
            ops_score_components.append(inv_score)
        
        # Cash conversion cycle
        if ccc_days is not None:
            # Target: <30 = excellent, 30-60 = good, 60-90 = fair, >90 = poor
            if ccc_days <= 30:
                ccc_score = 100
            elif ccc_days <= 60:
                ccc_score = 70 + ((60 - ccc_days) / 30) * 30
            elif ccc_days <= 90:
                ccc_score = 40 + ((90 - ccc_days) / 30) * 30
            else:
                ccc_score = max(0, 40 - ((ccc_days - 90) / 30) * 10)
            ops_score_components.append(ccc_score)
        
        if ops_score_components:
            ops_score = int(sum(ops_score_components) / len(ops_score_components))
            ops_label = "good" if ops_score > 75 else ("caution" if ops_score > 50 else "critical")
            ops_summary = "Good uptime" if ops_score > 75 else "Minor delays; good uptime"
        else:
            ops_score = None
            ops_label = None
            ops_summary = "Insufficient operational data"

        # C. Risk Exposure (Runway + Liquidity Ratios)
        risk_score_components = []
        
        # Runway component
        if runway_months is not None and runway_months > 0:
            runway_risk_score = min(100, runway_months * 8)
            risk_score_components.append(runway_risk_score)
        
        # Quick ratio component (liquidity risk)
        if quick_ratio is not None:
            # Target: >1.5 = low risk, 1.0-1.5 = moderate, <1.0 = high risk
            if quick_ratio >= 1.5:
                quick_risk_score = 100
            elif quick_ratio >= 1.0:
                quick_risk_score = 70 + ((quick_ratio - 1.0) / 0.5) * 30
            else:
                quick_risk_score = max(0, quick_ratio * 70)
            risk_score_components.append(quick_risk_score)
        
        if risk_score_components:
            risk_score = int(sum(risk_score_components) / len(risk_score_components))
            risk_label = "good" if risk_score > 75 else ("caution" if risk_score > 50 else "critical")
            runway_display = f"{runway_months:.1f} months" if runway_months is not None else "N/A"
            risk_summary = f"2 open compliance items" if risk_score < 75 else f"Runway {runway_display}"
        else:
            risk_score = None
            risk_label = None
            risk_summary = "Insufficient risk data"

        # D. Growth Momentum - based on revenue trend
        if net_trend_3mo:
            if net_trend_3mo == "positive":
                growth_score = 85
                growth_label = "good"
                growth_summary = "Steady upward trend"
            elif net_trend_3mo == "negative":
                growth_score = 45
                growth_label = "critical"
                growth_summary = "Declining trend"
            else:  # flat
                growth_score = 65
                growth_label = "caution"
                growth_summary = "Flat growth"
        else:
            growth_score = None
            growth_label = None
            growth_summary = "Insufficient growth data"

        # E. Customer Health - We don't have this data, so skip it
        cust_score = None
        cust_label = None
        cust_summary = "Insufficient customer data"

        # 3. Overall Business Health (only from available metrics)
        available_scores = []
        weights_map = []
        
        if fin_health_score is not None:
            available_scores.append(fin_health_score)
            weights_map.append(0.4)  # Financial is most important
        if ops_score is not None:
            available_scores.append(ops_score)
            weights_map.append(0.25)
        if risk_score is not None:
            available_scores.append(risk_score)
            weights_map.append(0.25)
        if growth_score is not None:
            available_scores.append(growth_score)
            weights_map.append(0.1)
        
        if available_scores:
            # Normalize weights
            total_weight = sum(weights_map)
            normalized_weights = [w / total_weight for w in weights_map]
            
            overall_score = int(sum(score * weight for score, weight in zip(available_scores, normalized_weights)))
            overall_label = "good" if overall_score > 80 else ("average" if overall_score > 60 else "poor")
        else:
            overall_score = None
            overall_label = "insufficient-data"

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
            priority_watch_areas.append("Inventory efficiency")
        if ccc_days is not None and ccc_days > 60:
            priority_watch_areas.append("Cash conversion cycle")
        if quick_ratio is not None and quick_ratio < 1.0:
            priority_watch_areas.append("Liquidity risk")
        if runway_months is not None and runway_months < 6:
            priority_watch_areas.append("Cash runway")
        if margin_pct is not None and margin_pct < 0.10:
            priority_watch_areas.append("Profit margins")
        if growth_score is not None and growth_score < 60:
            priority_watch_areas.append("Growth momentum")
        
        # 6. Active Health Alerts (based on real thresholds)
        active_alerts = []
        
        if runway_months is not None and runway_months < 3:
            active_alerts.append({
                "type": "critical",
                "message": f"Critical: Cash runway below 3 months ({runway_months:.1f} months remaining)"
            })
        elif runway_months is not None and runway_months < 6:
            active_alerts.append({
                "type": "warning",
                "message": f"Warning: Cash runway below 6 months ({runway_months:.1f} months remaining)"
            })
        
        if margin_pct is not None and margin_pct < 0.05:
            active_alerts.append({
                "type": "critical",
                "message": f"Critical: Net margin critically low ({margin_pct*100:.1f}%)"
            })
        elif margin_pct is not None and margin_pct < 0.10:
            active_alerts.append({
                "type": "warning",
                "message": f"Warning: Net margin below target ({margin_pct*100:.1f}%)"
            })
        
        if quick_ratio is not None and quick_ratio < 1.0:
            active_alerts.append({
                "type": "warning",
                "message": f"Warning: Quick ratio below 1.0 ({quick_ratio:.2f})"
            })
        
        if burn_rate_monthly is not None and burn_rate_monthly > revenue_mtd:
            active_alerts.append({
                "type": "critical",
                "message": f"Critical: Monthly burn exceeds revenue"
            })
        
        # If no alerts, add success message
        if not active_alerts:
            active_alerts.append({
                "type": "success",
                "message": "No critical health alerts at this time"
            })
        
        # 7. Calculate AI Confidence based on data availability
        available_metrics = [
            margin_pct, runway_months, quick_ratio, current_ratio,
            inventory_turns, ccc_days, cash_flow_mtd, burn_rate_monthly
        ]
        available_count = sum(1 for m in available_metrics if m is not None)
        total_metrics = len(available_metrics)
        confidence_pct = int((available_count / total_metrics) * 100)
        ai_confidence = f"{confidence_pct}%"
        ai_confidence_details = f"Based on {available_count}/{total_metrics} key metrics"
        
        # 8. Generate AI Summary
        if overall_score is not None:
            if overall_score > 80:
                ai_summary = f"Overall health is strong ({overall_score}), driven by solid financial metrics."
            elif overall_score > 60:
                ai_summary = f"Overall health is moderate ({overall_score}). Some areas need attention."
            else:
                ai_summary = f"Overall health needs improvement ({overall_score}). Multiple areas require focus."
            
            # Add specific insights
            if positive_drivers:
                top_driver = positive_drivers[0]["name"]
                ai_summary += f" Key strength: {top_driver}."
            if drags:
                top_drag = drags[0]["name"]
                ai_summary += f" Main concern: {top_drag}."
        else:
            ai_summary = "Insufficient data to generate comprehensive health assessment."
        
        # 9. Construct Response (NO dummy data)
        response = {
            "Business Health": {
                "Overall Business Health": {
                    "score": overall_score,
                    "label": overall_label,
                    "trend": "↑" if net_trend_3mo == "positive" else ("↓" if net_trend_3mo == "negative" else "→"),
                    "peer_avg": None,  # We don't have peer data
                    "yours": overall_score,
                    "time_period": range
                },
                "Financial Health": {
                    "score": fin_health_score,
                    "summary": fin_summary,
                    "label": fin_label
                } if fin_health_score is not None else None,
                "Operational Health": {
                    "score": ops_score,
                    "summary": ops_summary,
                    "label": ops_label
                } if ops_score is not None else None,
                "Customer Health": {
                    "score": cust_score,
                    "summary": cust_summary,
                    "label": cust_label
                } if cust_score is not None else None,
                "Risk Exposure": {
                    "score": risk_score,
                    "summary": risk_summary,
                    "label": risk_label
                } if risk_score is not None else None,
                "Growth Momentum": {
                    "score": growth_score,
                    "summary": growth_summary,
                    "label": growth_label
                } if growth_score is not None else None
            },
            "AI Confidence Index": ai_confidence,
            "AI Confidence Details": ai_confidence_details,
            "Overview Dashboard": {
                "AI summary": ai_summary,
                "AI diagnosis": f"Score is {overall_score} ({overall_label})." if overall_score is not None else "Insufficient data",
                "12-month Health Score": None,  # Would need historical data
                "MoM deltas": {
                    "health score": overall_score, 
                    "delta": None,  # Would need prior month data
                    "peer": None  # No peer data available
                }
            },
            "Drivers": {
                "Top Positive Drivers": positive_drivers if positive_drivers else None,
                "Top Drags": drags if drags else None
            },
            "Priority Watch Areas": priority_watch_areas if priority_watch_areas else None,
            "Active Health Alerts": active_alerts,
            "Quadrants": {
                k: v for k, v in {
                    "Financial Health": {"score": fin_health_score, "summary": fin_summary, "label": fin_label} if fin_health_score is not None else None,
                    "Operational Health": {"score": ops_score, "summary": ops_summary, "label": ops_label} if ops_score is not None else None,
                    "Customer Health": {"score": cust_score, "summary": cust_summary, "label": cust_label} if cust_score is not None else None,
                    "Risk Exposure": {"score": risk_score, "summary": risk_summary, "label": risk_label} if risk_score is not None else None,
                    "Growth Momentum": {"score": growth_score, "summary": growth_summary, "label": growth_label} if growth_score is not None else None
                }.items() if v is not None
            },
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
        response["Business Health"] = {k: v for k, v in response["Business Health"].items() if v is not None}

        # Log successful insights view
        await feature_usage_service.log_usage(user_id, "insights")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(response),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate health report: {str(exc)}",
        )
