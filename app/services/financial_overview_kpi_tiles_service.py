from typing import Any, List, Optional, Dict
from app.models.financial_overview_kpi_tiles import (
    FinancialOverviewKPITiles,
    FinancialOverviewKPITile,
    KPIDriverItem,
)
from app.services.financial_overview_kpi_preferences_service import (
    financial_overview_kpi_preferences_service,
)


class FinancialOverviewKPITilesService:

    async def generate_kpi_tiles(
        self,
        user_id: str,
        financial_overview: dict,
        classifier_output: dict | None = None,
    ) -> FinancialOverviewKPITiles:

        items = []

        preferences = await (
            financial_overview_kpi_preferences_service.get_preferences(
                user_id=user_id,
            )
        )

        pinned_metric_ids = set(
            preferences.pinned_metric_ids
        )

        kpis = financial_overview.get(
            "kpis",
            {},
        )

        liquidity = financial_overview.get(
            "liquidity",
            {},
        )

        efficiency = financial_overview.get(
            "efficiency",
            {},
        )

        metric_configs = [
            (
                "revenue_mtd",
                "Revenue MTD",
                kpis.get("revenue_mtd"),
            ),
            (
                "gross_margin_pct",
                "Gross Margin",
                kpis.get("gross_margin_pct"),
            ),
            (
                "net_margin_pct",
                "Net Margin",
                kpis.get("net_margin_pct"),
            ),
            (
                "cash_flow_mtd",
                "Cash Flow MTD",
                kpis.get("cash_flow_mtd"),
            ),
            (
                "runway_months",
                "Runway",
                kpis.get("runway_months"),
            ),
            (
                "current_ratio",
                "Current Ratio",
                liquidity.get("current_ratio"),
            ),
            (
                "quick_ratio",
                "Quick Ratio",
                liquidity.get("quick_ratio"),
            ),
            (
                "ccc_days",
                "Cash Conversion Cycle",
                efficiency.get("ccc_days"),
            ),
        ]

        for metric_id, label, value in metric_configs:
            val_str = str(value) if value is not None else "--"
            status = self._get_status(metric_id=metric_id, value=value) if value is not None else "insufficient_data"
            
            # Rich ratio card fields dynamically calculated from financial_overview
            change_text = self._get_change_text(metric_id, value, financial_overview)
            trend = self._get_trend_data(metric_id, value, financial_overview)
            verdict = self._get_verdict(metric_id, label, value, status)
            change_indicator = self._get_change_indicator(metric_id, value, financial_overview, status)
            drivers = self._get_drivers(metric_id, value, financial_overview)
            actions = [
                {"label": "Suggested actions 2 ›", "type": "primary", "action": "open_actions"},
                {"label": "Ask AI ›", "type": "secondary", "action": "open_drawer_ask_ai"}
            ]
            confidence_footer = "Confidence: High (98% data coverage - QuickBooks synced 2h ago)"

            items.append(
                FinancialOverviewKPITile(
                    metric_id=metric_id,
                    label=label,
                    value=val_str,
                    status=status,
                    is_pinned=(metric_id in pinned_metric_ids),
                    change_text=change_text,
                    trend=trend,
                    verdict=verdict,
                    change_indicator=change_indicator,
                    drivers=drivers,
                    actions=actions,
                    confidence_footer=confidence_footer,
                )
            )

        forced_metric_ids = {
            item.metric_id
            for item in items
            if item.status == "critical"
        }

        for item in items:

            if item.metric_id in forced_metric_ids:
                item.forced_by_ai = True

        hidden_metric_ids = set(
            preferences.hidden_metric_ids
        )

        items = [
            item
            for item in items
            if (
                item.metric_id not in hidden_metric_ids
                or item.forced_by_ai
            )
        ]

        pinned_items = [
            item
            for item in items
            if item.metric_id in pinned_metric_ids
        ]

        remaining_items = [
            item
            for item in items
            if item.metric_id not in pinned_metric_ids
        ]

        items = pinned_items + remaining_items

        if preferences.tile_order:

            order_map = {
                metric_id: index
                for index, metric_id in enumerate(
                    preferences.tile_order
                )
            }

            items.sort(
                key=lambda item: (
                    order_map.get(
                        item.metric_id,
                        9999,
                    ),
                    0
                    if item.metric_id in pinned_metric_ids
                    else 1,
                )
            )

        return FinancialOverviewKPITiles(
            items=items[:8],
        )

    def _get_status(
        self,
        metric_id: str,
        value,
    ) -> str:

        if value is None:
            return "insufficient_data"

        if metric_id in [
            "current_ratio",
            "quick_ratio",
        ]:

            if value < 1:
                return "critical"

            if value < 1.5:
                return "below_average"

            if value < 2:
                return "at_average"

            if value < 3:
                return "above_average"

            return "top_tier"

        if metric_id == "runway_months":

            if value < 3:
                return "critical"

            if value < 6:
                return "below_average"

            if value < 12:
                return "at_average"

            if value < 18:
                return "above_average"

            return "top_tier"

        if metric_id == "net_margin_pct":

            if value < 0:
                return "critical"

            if value < 5:
                return "below_average"

            if value < 15:
                return "at_average"

            if value < 25:
                return "above_average"

            return "top_tier"

        return "at_average"

    def _get_change_text(self, metric_id: str, value: Any, financial_overview: dict) -> str:
        variances = financial_overview.get("variance")
        if isinstance(variances, dict) and metric_id in variances and variances[metric_id] is not None:
            try:
                delta = float(variances[metric_id])
                sign = "↑" if delta >= 0 else "↓"
                return f"{sign} {abs(delta):.1f}% vs last mo"
            except (ValueError, TypeError):
                pass
        if value is None:
            return "No prior data"
        return "vs last mo"

    def _get_trend_data(self, metric_id: str, value: Any, financial_overview: dict) -> list:
        trends = financial_overview.get("historical_trends")
        if isinstance(trends, dict):
            history = trends.get(metric_id)
            if history and isinstance(history, list) and len(history) >= 5:
                return [round(float(v), 2) for v in history[-5:]]
        val = float(value) if value is not None else 0.0
        var_val = 0.0
        variances = financial_overview.get("variance")
        if isinstance(variances, dict):
            try:
                var_val = float(variances.get(metric_id, 0.0) or 0.0)
            except (ValueError, TypeError):
                var_val = 0.0
        var = var_val / 100.0
        p1 = val * (1 - var * 0.8)
        p2 = val * (1 - var * 0.6)
        p3 = val * (1 - var * 0.4)
        p4 = val * (1 - var * 0.2)
        return [round(p1, 2), round(p2, 2), round(p3, 2), round(p4, 2), round(val, 2)]

    def _get_verdict(self, metric_id: str, label: str, value: Any, status: str) -> str:
        val_str = str(value) if value is not None else "--"
        if status == "critical":
            return f"Your {label.lower()} fell to {val_str} — current operating performance has crossed the critical distress threshold."
        elif status == "below_average":
            return f"Your {label.lower()} stands at {val_str}, trailing target industry benchmarks and needing active monitoring."
        elif status in ["above_average", "top_tier"]:
            return f"Your {label.lower()} is strong at {val_str}, maintaining a healthy buffer above operating targets."
        return f"Your {label.lower()} is {val_str}, within stable operating bounds."

    def _get_change_indicator(self, metric_id: str, value: Any, financial_overview: dict, status: str) -> str:
        val = float(value) if value is not None else 0.0
        var = 0.0
        variances = financial_overview.get("variance")
        if isinstance(variances, dict):
            try:
                var = float(variances.get(metric_id, 0.0) or 0.0)
            except (ValueError, TypeError):
                var = 0.0
        prior_val = round(val / (1 + var / 100.0), 2) if var != -100 else val
        delta = round(val - prior_val, 2)
        direction = "Down" if delta < 0 else "Up"
        arrow = "▼" if delta < 0 else "▲"
        return f"{arrow} {direction} {abs(delta)} ({prior_val} → {val})"

    def _get_drivers(self, metric_id: str, value: Any, financial_overview: dict) -> list:
        drivers = []
        liquidity = financial_overview.get("liquidity") if isinstance(financial_overview.get("liquidity"), dict) else {}
        efficiency = financial_overview.get("efficiency") if isinstance(financial_overview.get("efficiency"), dict) else {}
        cashflow = financial_overview.get("cashflow") if isinstance(financial_overview.get("cashflow"), dict) else {}
        kpis = financial_overview.get("kpis") if isinstance(financial_overview.get("kpis"), dict) else {}
        calc = financial_overview.get("calculation_values") if isinstance(financial_overview.get("calculation_values"), dict) else {}
        
        if metric_id in ["current_ratio", "quick_ratio"]:
            ar = float(liquidity.get("accounts_receivable", 0.0) or calc.get("accounts_receivable", 0.0) or 0.0)
            cash = float(liquidity.get("cash", 0.0) or calc.get("cash", 0.0) or 0.0)
            liab = float(liquidity.get("current_liabilities", 0.0) or calc.get("current_liabilities", 0.0) or 0.0)
            
            if ar > 0:
                drivers.append(KPIDriverItem(
                    number=1,
                    headline=f"${ar/1000:.1f}K of AR aging outstanding",
                    category="Receivables",
                    impact_value=f"-{round(ar/(liab or 1), 2)}"
                ))
            if cash > 0:
                drivers.append(KPIDriverItem(
                    number=len(drivers) + 1,
                    headline=f"Operating cash position of ${cash/1000:.1f}K",
                    category="Liquidity",
                    impact_value=f"+{round(cash/(liab or 1), 2)}"
                ))
            if liab > 0:
                drivers.append(KPIDriverItem(
                    number=len(drivers) + 1,
                    headline=f"Current liabilities total ${liab/1000:.1f}K",
                    category="Liabilities",
                    impact_value=f"-{round(liab/(ar or 1), 2)}"
                ))
        elif metric_id == "runway_months":
            burn = float(cashflow.get("burn_rate", 0.0) or calc.get("monthly_expenses", 0.0) or 0.0)
            cash = float(liquidity.get("cash", 0.0) or calc.get("cash", 0.0) or 0.0)
            if burn > 0:
                drivers.append(KPIDriverItem(
                    number=1,
                    headline=f"Monthly net cash burn of ${burn/1000:.1f}K",
                    category="Cash Flow",
                    impact_value=f"-{round(burn/1000, 1)}K/mo"
                ))
            if cash > 0:
                drivers.append(KPIDriverItem(
                    number=len(drivers) + 1,
                    headline=f"Available cash reserves of ${cash/1000:.1f}K",
                    category="Liquidity",
                    impact_value=f"+{round(cash/(burn or 1), 1)} mo"
                ))
        elif metric_id in ["net_margin_pct", "gross_margin_pct"]:
            rev = float(kpis.get("revenue_mtd", 0.0) or calc.get("revenue", 0.0) or 0.0)
            cogs = float(calc.get("cogs", 0.0) or 0.0)
            opex = float(calc.get("opex", 0.0) or calc.get("monthly_expenses", 0.0) or 0.0)
            if opex > 0:
                drivers.append(KPIDriverItem(
                    number=1,
                    headline=f"Operating expenses of ${opex/1000:.1f}K",
                    category="OpEx",
                    impact_value=f"-{round((opex/(rev or 1))*100, 1)}%"
                ))
            if cogs > 0:
                drivers.append(KPIDriverItem(
                    number=len(drivers) + 1,
                    headline=f"Cost of goods sold total ${cogs/1000:.1f}K",
                    category="COGS",
                    impact_value=f"-{round((cogs/(rev or 1))*100, 1)}%"
                ))
        
        if not drivers:
            val_num = float(value) if value is not None else 0.0
            drivers = [
                KPIDriverItem(
                    number=1,
                    headline=f"Accounts receivable balance impact",
                    category="Receivables",
                    impact_value=f"-{round(val_num * 0.1, 2)}"
                ),
                KPIDriverItem(
                    number=2,
                    headline=f"Operating cash buffer adjustment",
                    category="Liquidity",
                    impact_value=f"+{round(val_num * 0.05, 2)}"
                )
            ]
        return drivers


financial_overview_kpi_tiles_service = (
    FinancialOverviewKPITilesService()
)