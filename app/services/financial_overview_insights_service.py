from app.models.financial_overview_insights import (
    FinancialOverviewInsights,
    FinancialOverviewInsightItem,
    ProfitabilityBanner,
)
from app.services.finance_analyst_service import (
    finance_analyst_service,
)


class FinancialOverviewInsightsService:

    async def generate_insights(
        self,
        user_id: str,
        financial_overview: dict,
        business_health: dict,
        classifier_output: dict | None = None,
    ):

        response = await finance_analyst_service.generate_financial_overview_insights(
            financial_overview=financial_overview,
            business_health=business_health,
            classifier_output=classifier_output,
        )

        return response


financial_overview_insights_service = (
    FinancialOverviewInsightsService()
)