from app.models.financial_overview_insights import (
    FinancialOverviewInsights,
    FinancialOverviewInsightItem,
    ProfitabilityBanner,
)
from app.services.finance_analyst_service import (
    finance_analyst_service,
)
from app.services.financial_overview_actions_service import (
    financial_overview_actions_service,
)


class FinancialOverviewInsightsService:

    async def generate_insights(
        self,
        user_id: str,
        financial_overview: dict,
        business_health: dict,
        classifier_output: dict | None = None,
    ):
        try:
            response = await finance_analyst_service.generate_financial_overview_insights(
                financial_overview=financial_overview,
                business_health=business_health,
                classifier_output=classifier_output,
            )
            if response and isinstance(response, dict) and "insights" in response:
                response["insights"] = await financial_overview_actions_service.apply_user_actions_to_insights(
                    user_id=user_id,
                    insights=response["insights"],
                )
            return response
        except Exception as e:
            print(f"[WARN] Failed to generate AI financial_overview_insights: {e}")
            return None


financial_overview_insights_service = (
    FinancialOverviewInsightsService()
)
