# backend/app/services/dashboard_service.py
"""
Dashboard Service
Orchestrates dashboard data aggregation with KPIs, deltas, colors, and alerts
"""
import asyncio
from datetime import datetime, timezone, timedelta
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from app.db import get_collection
from app.services.ai_insights_service import ai_insights_service
from app.services.gemini_service import GeminiService
from app.services.quickbooks_financial_service import QuickBooksFinancialService


class DashboardService:
    """
    Service for dashboard data aggregation.
    Computes KPIs, deltas, color indicators, and contextual alerts.
    """
    
    def __init__(self):
        self.qb_financial_service = QuickBooksFinancialService()
        self.manual_entries = get_collection("manual_entries")
        self.gemini_service = GeminiService()
    
    async def get_dashboard_data(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Legacy helper that returns KPI card data. Internally powered by the new
        dashboard summary pipeline so older callers keep working.
        """
        summary = await self.get_dashboard_summary(user_id=user_id)
        return {
            "kpis": summary.get("kpis", {}),
            "quick_actions": summary.get("quick_actions", []),
            "generated_at": summary.get("generated_at"),
        }

    async def get_dashboard_summary(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Full dashboard payload that powers KPI cards, mini badges, insights,
        alerts, trend summaries, and reminder previews.
        """
        (
            current_kpis,
            prior_kpis,
            financial_overview,
            manual_adjustments,
        ) = await asyncio.gather(
            self.qb_financial_service.get_dashboard_kpis(user_id),
            self._get_prior_period_kpis(user_id),
            self.qb_financial_service.get_financial_overview(user_id),
            self._get_manual_entry_adjustments(user_id),
        )

        adjusted_kpis = self._apply_manual_adjustments(current_kpis, manual_adjustments)
        ai_health_score = self._calculate_ai_health_score(financial_overview)
        prior_ai_health = self._calculate_ai_health_score_from_prior(prior_kpis, financial_overview)
        kpi_cards = self._build_kpi_cards(
            adjusted_kpis,
            prior_kpis,
            ai_health_score,
            prior_ai_health,
        )

        alerts_payload = await self.get_contextual_alerts(user_id=user_id)
        ai_components = self._build_ai_health_components(financial_overview, ai_health_score)
        trend_summaries = self._build_trend_summaries(adjusted_kpis, prior_kpis, financial_overview)
        badges = self._build_mini_badges(
            adjusted_kpis,
            prior_kpis,
            financial_overview,
            alerts_payload.get("alerts", []),
        )
        insights_summary = await self._get_dashboard_insights_summary(user_id, financial_overview)

        return {
            "kpis": kpi_cards,
            "trend_summaries": trend_summaries,
            "alerts": alerts_payload.get("alerts", []),
            "mini_badges": badges,
            "ai_health": ai_components,
            "ai_insights": insights_summary,
            "quick_actions": self._default_quick_actions(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _build_kpi_cards(
        self,
        current_kpis: Dict[str, Any],
        prior_kpis: Dict[str, Any],
        ai_health_score: int,
        prior_ai_health: int,
    ) -> Dict[str, Any]:
        """Construct KPI cards using the legacy helper for consistency."""
        return {
            "revenue_mtd": self._build_kpi_card(
                value=current_kpis.get("revenue_mtd", 0),
                prior_value=prior_kpis.get("revenue_mtd", 0),
                format_type="currency",
                link="/overview#revenue",
                thresholds={"green": 0.05, "yellow": -0.05},
            ),
            "net_margin_pct": self._build_kpi_card(
                value=current_kpis.get("net_margin_pct", 0),
                prior_value=prior_kpis.get("net_margin_pct", 0),
                format_type="percentage",
                link="/overview#margin",
                thresholds={"green": 0.15, "yellow": 0.08},
            ),
            "cash": self._build_kpi_card(
                value=current_kpis.get("cash", 0),
                prior_value=prior_kpis.get("cash", 0),
                format_type="currency",
                link="/overview#cash",
                thresholds={"green": 0, "yellow": -0.1},
            ),
            "runway_months": self._build_kpi_card(
                value=current_kpis.get("runway_months"),
                prior_value=prior_kpis.get("runway_months"),
                format_type="months",
                link="/overview#runway",
                thresholds={"green": 12, "yellow": 6},
            ),
            "ai_health_score": self._build_kpi_card(
                value=ai_health_score,
                prior_value=prior_ai_health,
                format_type="score",
                link="/overview#health",
                thresholds={"green": 70, "yellow": 50},
            ),
        }

    def _build_ai_health_components(
        self,
        financial_overview: Dict[str, Any],
        ai_health_score: int,
    ) -> Dict[str, Any]:
        """
        Build AI health score components so UI and Gemini explainers can surface
        why the score looks the way it does.
        """
        kpis = financial_overview.get("kpis", {})
        liquidity = financial_overview.get("liquidity", {})
        cashflow = financial_overview.get("cashflow", {})

        kpi_total = len(kpis) or 1
        kpi_populated = len([value for value in kpis.values() if value is not None])
        data_completeness = int(round((kpi_populated / kpi_total) * 100))

        liquidity_signals = [liquidity.get("current_ratio"), liquidity.get("quick_ratio")]
        mapping_completeness = int(
            round(
                (
                    len([value for value in liquidity_signals if value is not None])
                    / (len(liquidity_signals) or 1)
                )
                * 100
            )
        )

        forecast_confidence = int(round((kpis.get("ai_confidence_pct", 0.6) or 0.6) * 100))

        components = [
            {
                "label": "Data completeness",
                "score": data_completeness,
                "note": "Share of KPI fields populated from synced ledgers.",
            },
            {
                "label": "Categorization & compliance",
                "score": mapping_completeness,
                "note": "Liquidity ratios and classifications available for scoring.",
            },
            {
                "label": "Forecast confidence",
                "score": forecast_confidence,
                "note": "Model confidence derived from time-series depth and stability.",
            },
        ]

        return {
            "score": ai_health_score,
            "components": components,
        }

    def _build_trend_summaries(
        self,
        current_kpis: Dict[str, Any],
        prior_kpis: Dict[str, Any],
        financial_overview: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Summaries for revenue and expenses vs last month plus cash trend."""
        variance = financial_overview.get("variance", [])
        expenses_entry = next((item for item in variance if item.get("metric") == "Expenses"), None)

        revenue_delta_pct = self._delta_pct(
            current_kpis.get("revenue_mtd"),
            prior_kpis.get("revenue_mtd"),
        )
        expense_delta_pct = self._delta_pct(
            expenses_entry.get("actual") if expenses_entry else None,
            expenses_entry.get("forecast") if expenses_entry else None,
        )

        cashflow = financial_overview.get("cashflow", {})
        net_trend = cashflow.get("net_trend_3mo", "insufficient-data")

        return {
            "revenue_vs_last_month": self._trend_block("Revenue", revenue_delta_pct),
            "expense_vs_last_month": self._trend_block("Expenses", expense_delta_pct, positive_is_good=False),
            "cash_trend": {
                "label": "Cash flow trend",
                "direction": net_trend,
                "description": self._describe_cash_trend(net_trend, cashflow.get("burn_rate_monthly")),
            },
        }

    def _build_mini_badges(
        self,
        current_kpis: Dict[str, Any],
        prior_kpis: Dict[str, Any],
        financial_overview: Dict[str, Any],
        _alerts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Mini alert badges for quick scanning."""
        cash = current_kpis.get("cash") or 0
        runway = current_kpis.get("runway_months") or 0
        revenue_growth = self._delta_pct(current_kpis.get("revenue_mtd"), prior_kpis.get("revenue_mtd"))
        cash_flow = financial_overview.get("kpis", {}).get("cash_flow_mtd", 0)

        badges = []
        if cash < 50000 or runway < 6:
            badges.append(
                {
                    "type": "low_cash",
                    "label": "Low cash runway",
                    "active": True,
                    "message": f"{runway:.1f} months runway" if runway else "Connect accounts to calculate runway.",
                }
            )

        if cash_flow is not None and cash_flow < 0:
            badges.append(
                {
                    "type": "spending_spike",
                    "label": "Spending spike",
                    "active": True,
                    "message": f"Cash flow is ${cash_flow:,.0f} MTD.",
                }
            )

        if revenue_growth and revenue_growth > 0.05:
            badges.append(
                {
                    "type": "ahead_of_target",
                    "label": "Ahead of target",
                    "active": True,
                    "message": f"Revenue up {revenue_growth * 100:.1f}% vs last month.",
                }
            )

        if not badges:
            badges.append(
                {
                    "type": "stable",
                    "label": "On track",
                    "active": True,
                    "message": "No urgent issues detected this week.",
                }
            )

        return badges

    async def _get_dashboard_insights_summary(
        self,
        user_id: str,
        financial_overview: Dict[str, Any],
    ) -> List[str]:
        insights_payload = await ai_insights_service.get_latest_insights(
            user_id=user_id,
            financial_data=financial_overview,
            business_profile=None,
        )
        summaries: List[str] = []
        for insight in insights_payload.get("insights", []):
            summaries.append(f"{insight.get('title')}: {insight.get('description')}")
        return summaries[:3]

    async def _get_manual_entry_adjustments(self, user_id: str) -> Dict[str, float]:
        """Aggregate manual entries for current month to adjust KPIs."""
        start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (start_of_month + timedelta(days=32)).replace(day=1)

        cursor = self.manual_entries.find(
            {
                "user_id": user_id,
                "occurred_on": {"$gte": start_of_month, "$lt": next_month},
            }
        )
        entries = await cursor.to_list(length=None)

        revenue_delta = 0.0
        cash_delta = 0.0
        for entry in entries:
            amount = float(entry.get("amount", 0) or 0)
            if entry.get("entry_type") == "income":
                revenue_delta += amount
                cash_delta += amount
            else:
                revenue_delta -= amount  # treat expenses as drag on revenue KPI
                cash_delta -= amount

        return {
            "revenue_delta": revenue_delta,
            "cash_delta": cash_delta,
        }

    def _apply_manual_adjustments(
        self,
        kpis: Dict[str, Any],
        adjustments: Dict[str, float],
    ) -> Dict[str, Any]:
        """Apply manual entry adjustments to KPI snapshot."""
        adjusted = dict(kpis)
        adjusted["revenue_mtd"] = (adjusted.get("revenue_mtd") or 0) + adjustments.get("revenue_delta", 0)
        adjusted["cash"] = (adjusted.get("cash") or 0) + adjustments.get("cash_delta", 0)
        return adjusted

    def _default_quick_actions(self) -> List[Dict[str, str]]:
        return [
            {"label": "Quick Forecast", "route": "/dashboard/forecast"},
            {"label": "Add Revenue/Expense", "route": "/transactions/manual"},
            {"label": "Ask AI Advisor", "route": "/ai/advisor"},
            {"label": "Financial Overview", "route": "/overview"},
        ]

    def _trend_block(
        self,
        label: str,
        delta_pct: Optional[float],
        *,
        positive_is_good: bool = True,
    ) -> Dict[str, Any]:
        if delta_pct is None:
            return {
                "label": label,
                "direction": "insufficient-data",
                "description": "Need more history to compute trend.",
            }

        if delta_pct > 0:
            direction = "up"
            good = positive_is_good
        elif delta_pct < 0:
            direction = "down"
            good = not positive_is_good
        else:
            direction = "flat"
            good = None

        descriptor = "improving" if good else "declining" if good is False else "flat"
        return {
            "label": label,
            "direction": direction,
            "delta_pct": delta_pct,
            "description": f"{label} {descriptor} {abs(delta_pct) * 100:.1f}% vs last month."
            if delta_pct != 0
            else f"{label} unchanged vs last month.",
        }

    def _delta_pct(self, current: Optional[float], prior: Optional[float]) -> Optional[float]:
        if current is None or prior in (None, 0):
            return None
        return (current - prior) / abs(prior)

    def _describe_cash_trend(self, trend: str, burn_rate: Optional[float]) -> str:
        if trend == "positive":
            return "Net cash improving over the last 3 months."
        if trend == "negative":
            burn = f" Burn rate ${burn_rate:,.0f}/mo." if burn_rate else ""
            return f"Cash trending down over the last quarter.{burn}"
        if trend == "flat":
            return "Cash roughly flat month-over-month."
        return "Need more data to determine cash trend."

    def _forecast_band(self, expected_value: float) -> Dict[str, Any]:
        spread = expected_value * 0.1
        return {
            "expected": expected_value,
            "range": {
                "low": expected_value - spread,
                "high": expected_value + spread,
            },
        }

    def _serialize_datetime(self, value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            return value
        return datetime.now(timezone.utc).isoformat()


    
    async def get_contextual_alerts(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Generate contextual alerts based on financial thresholds.
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with alerts array
        """
        # Fetch current KPIs
        current_kpis = await self.qb_financial_service.get_dashboard_kpis(user_id)
        
        # Fetch full overview for additional metrics
        financial_overview = await self.qb_financial_service.get_financial_overview(user_id)
        
        alerts = []
        
        # Alert: Low cash runway
        runway = current_kpis.get("runway_months")
        if runway and runway < 6:
            alerts.append({
                "level": "critical" if runway < 3 else "warning",
                "title": "Low Cash Runway",
                "message": f"Current runway of {runway:.1f} months is below recommended threshold.",
                "action": "Review expenses and explore financing options",
                "metric": "runway_months"
            })
        
        # Alert: Margin drop
        net_margin = current_kpis.get("net_margin_pct")
        if net_margin and net_margin < 0.05:  # Less than 5%
            alerts.append({
                "level": "warning",
                "title": "Low Net Margin",
                "message": f"Net margin of {net_margin*100:.1f}% is below healthy threshold.",
                "action": "Review pricing strategy and cost structure",
                "metric": "net_margin_pct"
            })
        
        # Alert: Negative cash flow
        kpis = financial_overview.get("kpis", {})
        cash_flow_mtd = kpis.get("cash_flow_mtd")
        if cash_flow_mtd and cash_flow_mtd < 0:
            alerts.append({
                "level": "warning",
                "title": "Negative Cash Flow",
                "message": f"Month-to-date cash flow is ${cash_flow_mtd:,.2f}.",
                "action": "Monitor collections and manage payables",
                "metric": "cash_flow_mtd"
            })
        
        # Alert: Poor liquidity
        liquidity = financial_overview.get("liquidity", {})
        current_ratio = liquidity.get("current_ratio")
        if current_ratio and current_ratio < 1.0:
            alerts.append({
                "level": "warning",
                "title": "Low Liquidity Ratio",
                "message": f"Current ratio of {current_ratio:.2f} indicates potential liquidity concerns.",
                "action": "Review current assets and liabilities",
                "metric": "current_ratio"
            })
        
        # Alert: High burn rate
        cashflow = financial_overview.get("cashflow", {})
        burn_rate = cashflow.get("burn_rate_monthly")
        if burn_rate and burn_rate > 0:
            cash = current_kpis.get("cash", 0)
            if cash > 0 and (cash / burn_rate) < 3:  # Less than 3 months at current burn
                alerts.append({
                    "level": "critical",
                    "title": "High Burn Rate",
                    "message": f"Monthly burn of ${burn_rate:,.2f} is consuming cash rapidly.",
                    "action": "Implement immediate cost reduction measures",
                    "metric": "burn_rate_monthly"
                })
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }



    async def record_manual_entry(
        self,
        user_id: str,
        *,
        entry_type: str,
        amount: float,
        category: str,
        label: str,
        occurred_on: datetime,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist manual revenue or expense rows for dashboard adjustments."""
        document = {
            "user_id": user_id,
            "entry_type": entry_type,
            "amount": amount,
            "category": category,
            "label": label or category,
            "occurred_on": occurred_on,
            "notes": notes,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.manual_entries.insert_one(document)
        document["id"] = str(result.inserted_id)
        document.pop("_id", None)
        return document

    async def run_quick_forecast(
        self,
        user_id: str,
        horizon_days: int,
    ) -> Dict[str, Any]:
        """Simple revenue & cash projection for the requested horizon."""
        summary = await self.get_dashboard_summary(user_id=user_id)
        today = datetime.now(timezone.utc).date()
        days_elapsed = max(today.day, 1)

        revenue_card = summary["kpis"]["revenue_mtd"]
        margin_card = summary["kpis"]["net_margin_pct"]
        cash_card = summary["kpis"]["cash"]

        revenue_mtd = revenue_card.get("value") or 0.0
        net_margin_pct = margin_card.get("value") or 0.1
        cash_balance = cash_card.get("value") or 0.0

        daily_revenue = revenue_mtd / days_elapsed
        daily_profit = daily_revenue * net_margin_pct
        projected_revenue = daily_revenue * horizon_days
        projected_cash = cash_balance + (daily_profit * horizon_days)

        return {
            "horizon_days": horizon_days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "forecast": {
                "revenue": self._forecast_band(projected_revenue),
                "cash": self._forecast_band(projected_cash),
                "assumptions": {
                    "daily_revenue": daily_revenue,
                    "net_margin_pct": net_margin_pct,
                },
            },
        }

    async def get_ai_dashboard_insights(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        financial_overview = await self.qb_financial_service.get_financial_overview(user_id)
        return await ai_insights_service.get_latest_insights(
            user_id=user_id,
            financial_data=financial_overview,
            business_profile=None,
        )

    async def explain_dashboard_with_gemini(
        self,
        user_id: str,
        persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        summary = await self.get_dashboard_summary(user_id=user_id)
        payload = {
            "company_profile": {"id": user_id},
            "kpis": summary.get("kpis"),
            "alerts": summary.get("alerts"),
            "persona": persona,
        }
        return await self.gemini_service.explain_dashboard(payload)

    async def explain_ai_health_with_gemini(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        financial_overview = await self.qb_financial_service.get_financial_overview(user_id)
        score = self._calculate_ai_health_score(financial_overview)
        components = self._build_ai_health_components(financial_overview, score)
        payload = {
            "score": components.get("score"),
            "components": components.get("components"),
        }
        return await self.gemini_service.explain_ai_health(payload)
    
    async def _get_prior_period_kpis(self, user_id: str) -> Dict[str, Any]:
        """
        Get prior period KPIs for delta calculation.
        Currently uses last month's data.
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with prior period KPIs
        """
        # For now, we'll fetch the full overview which includes last month data
        # In the future, we could add a dedicated method to fetch specific prior periods
        try:
            overview = await self.qb_financial_service.get_financial_overview(user_id)
            
            # Extract last month values from variance data
            variance = overview.get("variance", [])
            
            # Build prior KPIs from variance forecast values (which represent prior period)
            prior_kpis = {}
            for item in variance:
                metric = item.get("metric", "")
                forecast = item.get("forecast", 0)
                
                if metric == "Revenue":
                    prior_kpis["revenue_mtd"] = forecast
                elif metric == "Net Profit":
                    # Calculate prior net margin
                    prior_revenue = next((v.get("forecast", 1) for v in variance if v.get("metric") == "Revenue"), 1)
                    if prior_revenue:
                        prior_kpis["net_margin_pct"] = forecast / prior_revenue
            
            # For cash and runway, we don't have historical data easily available
            # So we'll use current values (delta will be 0)
            current_kpis = await self.qb_financial_service.get_dashboard_kpis(user_id)
            prior_kpis["cash"] = current_kpis.get("cash", 0)
            prior_kpis["runway_months"] = current_kpis.get("runway_months")
            
            return prior_kpis
        except Exception as e:
            print(f"Error fetching prior period KPIs: {e}")
            # Return empty dict if we can't fetch prior data
            return {}
    
    def _calculate_ai_health_score(self, financial_overview: Dict[str, Any]) -> int:
        """
        Calculate AI Health Score based on financial metrics.
        
        Composite score (0-100):
        - Financial health (40%): Net Margin, Current Ratio, Quick Ratio
        - Cash flow health (30%): Runway months, burn rate trend
        - Growth indicators (30%): Revenue trend, margin improvement
        
        Args:
            financial_overview: Full financial overview data
        
        Returns:
            Health score (0-100)
        """
        scores = []
        weights = []
        
        kpis = financial_overview.get("kpis", {})
        liquidity = financial_overview.get("liquidity", {})
        cashflow = financial_overview.get("cashflow", {})
        
        # Financial health (40%)
        financial_health_score = 0
        financial_health_count = 0
        
        # Net margin score (0-100)
        net_margin = kpis.get("net_margin_pct")
        if net_margin is not None:
            # >20% = 100, 15% = 80, 10% = 60, 5% = 40, 0% = 20, <0% = 0
            margin_score = min(100, max(0, (net_margin * 500)))  # 0.20 * 500 = 100
            financial_health_score += margin_score
            financial_health_count += 1
        
        # Current ratio score
        current_ratio = liquidity.get("current_ratio")
        if current_ratio is not None:
            # >2.0 = 100, 1.5 = 80, 1.0 = 50, 0.5 = 25, 0 = 0
            ratio_score = min(100, max(0, current_ratio * 50))
            financial_health_score += ratio_score
            financial_health_count += 1
        
        # Quick ratio score
        quick_ratio = liquidity.get("quick_ratio")
        if quick_ratio is not None:
            # >1.5 = 100, 1.0 = 70, 0.5 = 35, 0 = 0
            quick_score = min(100, max(0, quick_ratio * 70))
            financial_health_score += quick_score
            financial_health_count += 1
        
        if financial_health_count > 0:
            scores.append(financial_health_score / financial_health_count)
            weights.append(0.4)
        
        # Cash flow health (30%)
        cashflow_health_score = 0
        cashflow_health_count = 0
        
        # Runway score
        runway = cashflow.get("runway_months")
        if runway is not None:
            # >18 months = 100, 12 = 80, 6 = 50, 3 = 25, 0 = 0
            runway_score = min(100, max(0, (runway / 18) * 100))
            cashflow_health_score += runway_score
            cashflow_health_count += 1
        
        # Burn rate trend (positive cash flow = good)
        burn_rate = cashflow.get("burn_rate_monthly")
        if burn_rate is not None:
            # Negative or zero burn = 100, positive burn scaled
            if burn_rate <= 0:
                burn_score = 100
            else:
                # Lower burn is better (this is simplified)
                burn_score = 50
            cashflow_health_score += burn_score
            cashflow_health_count += 1
        
        if cashflow_health_count > 0:
            scores.append(cashflow_health_score / cashflow_health_count)
            weights.append(0.3)
        
        # Growth indicators (30%)
        growth_score = 0
        growth_count = 0
        
        # Revenue trend
        net_trend = cashflow.get("net_trend_3mo", "insufficient-data")
        if net_trend == "positive":
            growth_score += 100
            growth_count += 1
        elif net_trend == "flat":
            growth_score += 60
            growth_count += 1
        elif net_trend == "negative":
            growth_score += 20
            growth_count += 1
        
        # Gross margin (higher is better)
        gross_margin = kpis.get("gross_margin_pct")
        if gross_margin is not None:
            # >40% = 100, 30% = 75, 20% = 50, 10% = 25
            gm_score = min(100, max(0, gross_margin * 250))
            growth_score += gm_score
            growth_count += 1
        
        if growth_count > 0:
            scores.append(growth_score / growth_count)
            weights.append(0.3)
        
        # Calculate weighted average
        if not scores:
            return 50  # Default neutral score
        
        total_weight = sum(weights)
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        
        return int(round(weighted_score))
    
    def _calculate_ai_health_score_from_prior(
        self,
        prior_kpis: Dict[str, Any],
        current_overview: Dict[str, Any]
    ) -> int:
        """
        Estimate prior period AI health score.
        Simplified version using available prior data.
        """
        # If we don't have prior data, return current score
        if not prior_kpis:
            return self._calculate_ai_health_score(current_overview)
        
        # Simplified calculation with available prior data
        # This is a rough estimate since we don't have full prior overview
        return 65  # Default prior score for delta calculation
    
    def _build_kpi_card(
        self,
        value: Optional[float],
        prior_value: Optional[float],
        format_type: str,
        link: str,
        thresholds: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Build a KPI card with value, delta, color, and link.
        
        Args:
            value: Current value
            prior_value: Prior period value
            format_type: How to format the value (currency, percentage, months, score)
            link: Navigation link
            thresholds: Color thresholds (green, yellow)
        
        Returns:
            KPI card dict
        """
        # Handle None values
        if value is None:
            return {
                "value": None,
                "delta": None,
                "delta_label": "N/A",
                "color": "gray",
                "link": link
            }
        
        # Calculate delta
        delta = None
        delta_label = "N/A"
        if prior_value is not None and prior_value != 0:
            if format_type in ["currency", "months", "score"]:
                delta = value - prior_value
            else:  # percentage
                delta = value - prior_value
        
        # Format delta label
        if delta is not None:
            if format_type == "currency":
                delta_label = f"${abs(delta):,.2f}" if delta >= 0 else f"-${abs(delta):,.2f}"
                delta_label = f"+{delta_label}" if delta > 0 else delta_label
            elif format_type == "percentage":
                delta_pct = delta * 100
                delta_label = f"+{delta_pct:.1f}%" if delta > 0 else f"{delta_pct:.1f}%"
            elif format_type == "months":
                delta_label = f"+{delta:.1f} mo" if delta > 0 else f"{delta:.1f} mo"
            elif format_type == "score":
                delta_label = f"+{int(delta)} pts" if delta > 0 else f"{int(delta)} pts"
        
        # Determine color
        color = self._determine_color(value, prior_value, format_type, thresholds)
        
        return {
            "value": value,
            "delta": delta,
            "delta_label": delta_label,
            "color": color,
            "link": link
        }
    
    def _determine_color(
        self,
        value: float,
        prior_value: Optional[float],
        format_type: str,
        thresholds: Dict[str, float],
    ) -> str:
        """
        Determine color indicator (green, yellow, red) based on value and thresholds.
        
        Args:
            value: Current value
            prior_value: Prior period value
            format_type: Value format type
            thresholds: Dict with 'green' and 'yellow' threshold values
        
        Returns:
            Color string: "green", "yellow", or "red"
        """
        green_threshold = thresholds.get("green", 0)
        yellow_threshold = thresholds.get("yellow", 0)
        
        # For absolute value thresholds (margins, runway, score)
        if format_type in ["percentage", "months", "score"]:
            if value >= green_threshold:
                return "green"
            elif value >= yellow_threshold:
                return "yellow"
            else:
                return "red"
        
        # For delta-based thresholds (revenue, cash)
        if prior_value is not None and prior_value != 0:
            delta_pct = (value - prior_value) / abs(prior_value)
            if delta_pct >= green_threshold:
                return "green"
            elif delta_pct >= yellow_threshold:
                return "yellow"
            else:
                return "red"
        
        # Default to yellow if we can't determine
        return "yellow"


# Singleton instance
dashboard_service = DashboardService()
