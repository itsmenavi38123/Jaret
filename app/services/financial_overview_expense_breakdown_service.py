from app.models.financial_overview_expense_breakdown import (
    FinancialOverviewExpenseBreakdown,
)


class FinancialOverviewExpenseBreakdownService:

    async def generate_expense_breakdown(
        self,
        financial_overview: dict,
        classifier_output: dict | None = None,
    ) -> FinancialOverviewExpenseBreakdown:

        return FinancialOverviewExpenseBreakdown(
            categories=[],
        )


financial_overview_expense_breakdown_service = (
    FinancialOverviewExpenseBreakdownService()
)