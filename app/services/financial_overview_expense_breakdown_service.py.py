from app.models.financial_overview_expense_breakdown import (
    FinancialOverviewExpenseBreakdown,
    ExpenseBreakdownCategory,
)


class FinancialOverviewExpenseBreakdownService:

    async def generate_expense_breakdown(
        self,
        financial_overview: dict,
        classifier_output: dict | None = None,
    ) -> FinancialOverviewExpenseBreakdown:

        calculation_values = financial_overview.get(
            "calculation_values",
            {},
        )

        cogs = float(
            calculation_values.get(
                "cogs",
                0,
            )
            or 0
        )

        opex = float(
            calculation_values.get(
                "opex",
                0,
            )
            or 0
        )

        total_expenses = cogs + opex

        categories = []

        if cogs > 0:
            categories.append(
                ExpenseBreakdownCategory(
                    category="Cost of Goods Sold",
                    amount=cogs,
                    percentage=(
                        round(
                            (cogs / total_expenses) * 100,
                            2,
                        )
                        if total_expenses
                        else 0
                    ),
                )
            )

        if opex > 0:
            categories.append(
                ExpenseBreakdownCategory(
                    category="Operating Expenses",
                    amount=opex,
                    percentage=(
                        round(
                            (opex / total_expenses) * 100,
                            2,
                        )
                        if total_expenses
                        else 0
                    ),
                )
            )

        return FinancialOverviewExpenseBreakdown(
            categories=categories,
        )


financial_overview_expense_breakdown_service = (
    FinancialOverviewExpenseBreakdownService()
)