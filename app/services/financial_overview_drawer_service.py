import json

from app.services.openai_service import (
    OpenAIService,
)
from app.services.claude_service import (
    claude_service,
)
from app.services.financial_overview_drawer_prompt import (
    FINANCIAL_OVERVIEW_DRAWER_PROMPT,
)


class FinancialOverviewDrawerService:

    def __init__(self):
        self.ai_service = OpenAIService()

    async def explain(
        self,
        payload: dict,
    ):

        prompt = self._build_financial_overview_prompt(
            payload,
        )

        return await claude_service.json_completion(
            system_prompt=(
                "You are the LightSignal Financial Analyst. "
                "Follow instructions strictly."
            ),
            user_content=prompt,
            temperature=0.2,
            max_tokens=4000,
        )

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
        return await self.ai_service.ask_kpi_ai(
            payload=payload,
        )


financial_overview_drawer_service = (
    FinancialOverviewDrawerService()
)