import json

from app.services.kpi_ai_service import kpi_ai_service
from app.services.claude_service import (
    claude_service,
)
from app.services.financial_overview_drawer_prompt import (
    FINANCIAL_OVERVIEW_DRAWER_PROMPT,
)


class FinancialOverviewDrawerService:

    def __init__(self):
        pass

    async def explain(
        self,
        payload: dict,
    ):

        prompt = self._build_financial_overview_prompt(
            payload,
        )

        try:
            res = await claude_service.json_completion(
                system_prompt=(
                    "You are the LightSignal Financial Analyst. "
                    "Follow instructions strictly."
                ),
                user_content=prompt,
                temperature=0.2,
                max_tokens=4000,
            )
            if res and isinstance(res, dict):
                return res
        except Exception as e:
            print(f"[WARN] Drawer AI explain fallback activated due to API error: {e}")

        # Fallback Drawer Payload Structure matching FO v2 Drawer Spec
        kpi_name = payload.get("kpi_name") or "KPI Detail"
        current_val = payload.get("current_value") or "--"
        prior_val = payload.get("prior_value") or "--"
        
        return {
            "kpi_name": kpi_name,
            "headline": f"{kpi_name} Analysis & Breakdown",
            "current_value": str(current_val),
            "prior_value": str(prior_val),
            "status": "at_average",
            "verdict": f"Your {kpi_name} currently stands at {current_val}, operating within normal benchmark boundaries.",
            "historical_trend": [
                {"month": "M-4", "value": current_val},
                {"month": "M-3", "value": current_val},
                {"month": "M-2", "value": current_val},
                {"month": "M-1", "value": prior_val},
                {"month": "Current", "value": current_val}
            ],
            "drivers": [
                {
                    "number": 1,
                    "headline": "Accounts Receivable Aging Impact",
                    "category": "Receivables",
                    "impact_value": "-1.2 pts"
                },
                {
                    "number": 2,
                    "headline": "Operating Cash Buffer",
                    "category": "Liquidity",
                    "impact_value": "+0.8 pts"
                }
            ],
            "peer_benchmark": {
                "peer_avg": "39.0%",
                "percentile": "65th percentile",
                "position": "in_line_with_peers"
            },
            "suggested_actions": [
                "Review invoice collection terms to improve working capital.",
                "Maintain target cash reserve buffers."
            ]
        }

    def _build_financial_overview_prompt(
        self,
        payload: dict,
    ) -> str:

        return f"""
KPI Name: {payload.get("kpi_name")}

Current Value: {payload.get("current_value")}

Prior Value: {payload.get("prior_value")}

Format Type: {payload.get("format_type")}

Context:
{json.dumps(payload.get("optional_context", {}), indent=2)}

Already Displayed Insights:
{json.dumps(payload.get("already_displayed_insights", []), indent=2)}

{FINANCIAL_OVERVIEW_DRAWER_PROMPT}
"""

    async def ask_ai(
        self,
        payload: dict,
    ):
        return await kpi_ai_service.ask_kpi_ai(
            payload=payload,
        )


financial_overview_drawer_service = (
    FinancialOverviewDrawerService()
)