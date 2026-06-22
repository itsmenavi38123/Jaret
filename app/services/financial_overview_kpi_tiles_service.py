from app.models.financial_overview_kpi_tiles import (
    FinancialOverviewKPITiles,
    FinancialOverviewKPITile,
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

            items.append(
                FinancialOverviewKPITile(
                    metric_id=metric_id,
                    label=label,
                    value=(
                        str(value)
                        if value is not None
                        else "--"
                    ),
                    status=(
                        self._get_status(
                            metric_id=metric_id,
                            value=value,
                        )
                        if value is not None
                        else "insufficient_data"
                    ),
                    is_pinned=(
                        metric_id in pinned_metric_ids
                    ),
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


financial_overview_kpi_tiles_service = (
    FinancialOverviewKPITilesService()
)