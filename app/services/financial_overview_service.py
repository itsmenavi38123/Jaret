from typing import Dict, Any

from app.services.quickbooks_financial_service import (
    quickbooks_financial_service,
)
from app.services.business_health_engine_service import (
    business_health_engine_service,
)
from app.services.financial_overview_insights_service import (
    financial_overview_insights_service,
)
from app.services.financial_overview_kpi_tiles_service import (
    financial_overview_kpi_tiles_service,
)
from app.services.financial_overview_expense_breakdown_service import (
    financial_overview_expense_breakdown_service,
)


class FinancialOverviewService:

    async def get_financial_overview_v2(
        self,
        user_id: str,
        classifier_output: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        financial_overview = (
            await quickbooks_financial_service.get_financial_overview(
                user_id=user_id,
            )
        )

        if not financial_overview:
            return {
                "connected": False,
                "profitability_banner": None,
                "financial_signals": {
                    "hero_signal": None,
                    "swipe_signals": [],
                    "items": [],
                    "signal_count": 0
                },
                "kpi_tiles": [],
                "expense_breakdown": [],
                "meta": {
                    "connected": False,
                    "is_demo": False,
                    "message": "Connect your accounting system to view financial overview"
                }
            }

        try:
            business_health = (
                await business_health_engine_service.generate_business_health(
                    user_id=user_id,
                    financial_overview=financial_overview,
                    classifier_output=classifier_output or {},
                )
            )
        except Exception as e:
            print(f"[WARN] Failed to generate business_health: {e}")
            business_health = {}

        financial_signals = business_health.get(
            "financial_signals",
            {},
        )

        try:
            financial_overview_insights = (
                await financial_overview_insights_service.generate_insights(
                    user_id=user_id,
                    financial_overview=financial_overview,
                    business_health=business_health,
                    classifier_output=classifier_output or {},
                )
            )
        except Exception as e:
            print(f"[WARN] Failed to generate financial_overview_insights: {e}")
            financial_overview_insights = None

        try:
            kpi_tiles = (
                await financial_overview_kpi_tiles_service.generate_kpi_tiles(
                    user_id=user_id,
                    financial_overview=financial_overview,
                    classifier_output=classifier_output or {},
                )
            )
        except Exception as e:
            print(f"[WARN] Failed to generate kpi_tiles: {e}")
            kpi_tiles = []

        try:
            expense_breakdown = (
                await financial_overview_expense_breakdown_service.generate_expense_breakdown(
                    user_id=user_id,
                    financial_overview=financial_overview,
                    classifier_output=classifier_output or {},
                )
            )
        except Exception as e:
            print(f"[WARN] Failed to generate expense_breakdown: {e}")
            expense_breakdown = []

        kpi_tiles_list = (
            [t.model_dump() if hasattr(t, "model_dump") else (t.dict() if hasattr(t, "dict") else t) for t in kpi_tiles.items]
            if hasattr(kpi_tiles, "items")
            else (kpi_tiles if isinstance(kpi_tiles, list) else [])
        )

        # Build clean Insights Mode & Profitability Banner objects
        insights_data = financial_overview_insights if isinstance(financial_overview_insights, dict) else {}
        profitability_banner = insights_data.get("profitability_banner")
        
        if not profitability_banner:
            kpis_data = financial_overview.get("kpis", {}) if isinstance(financial_overview, dict) else {}
            net_margin = kpis_data.get("net_margin_pct")
            rev_mtd = kpis_data.get("revenue_mtd")
            
            if net_margin is not None or (rev_mtd is not None and rev_mtd > 0):
                nm_val = float(net_margin or 0.0)
                if nm_val >= 0.15:
                    profitability_banner = {
                        "status": "above_average",
                        "headline": f"Profitable — Net margin at {nm_val * 100:.1f}%",
                        "supporting_text": "Financial performance is healthy and exceeding standard operating targets."
                    }
                elif nm_val >= 0.05:
                    profitability_banner = {
                        "status": "at_average",
                        "headline": f"Profitable — Net margin at {nm_val * 100:.1f}%",
                        "supporting_text": "Financial performance is stable within normal operating bounds."
                    }
                elif nm_val >= 0.0:
                    profitability_banner = {
                        "status": "below_average",
                        "headline": f"Near break-even — Net margin at {nm_val * 100:.1f}%",
                        "supporting_text": "Profitability is tight this period; monitor operating expenses closely."
                    }
                else:
                    profitability_banner = {
                        "status": "critical",
                        "headline": f"Operating at a net loss ({nm_val * 100:.1f}%)",
                        "supporting_text": "Operating expenses currently exceed revenue for this reporting period."
                    }
            else:
                profitability_banner = None

        items = insights_data.get("items") or insights_data.get("insights") or []
        hero_signal = items[0] if items else (financial_signals.get("hero_signal") if isinstance(financial_signals, dict) else None)
        swipe_signals = items[1:] if len(items) > 1 else (financial_signals.get("swipe_signals") if isinstance(financial_signals, dict) else [])

        clean_financial_signals = {
            "hero_signal": hero_signal,
            "swipe_signals": swipe_signals,
            "items": items,
            "signal_count": len(items) if items else (len(swipe_signals) + (1 if hero_signal else 0))
        }

        kpi_tiles_list = (
            [t.model_dump() if hasattr(t, "model_dump") else (t.dict() if hasattr(t, "dict") else t) for t in kpi_tiles.items]
            if hasattr(kpi_tiles, "items")
            else (kpi_tiles if isinstance(kpi_tiles, list) else [])
        )

        return {
            "profitability_banner": profitability_banner,
            "financial_signals": clean_financial_signals,
            "kpi_tiles": kpi_tiles_list,
            "expense_breakdown": expense_breakdown,
        }


financial_overview_service = FinancialOverviewService()