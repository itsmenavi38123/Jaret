from datetime import datetime, timezone

from app.models.financial_overview_expense_breakdown import (
    FinancialOverviewExpenseBreakdown,
    ExpenseCategory,
)

from app.services.quickbooks_financial_service import (
    quickbooks_financial_service,
)


class FinancialOverviewExpenseBreakdownService:

    async def generate_expense_breakdown(
        self,
        user_id: str,
        financial_overview: dict,
        classifier_output: dict | None = None,
    ) -> FinancialOverviewExpenseBreakdown:

        today = datetime.now(
            timezone.utc
        ).date()

        vendors = (
            await quickbooks_financial_service.get_expense_by_vendor(
                user_id=user_id,
                start_date=today.replace(
                    day=1,
                ),
                end_date=today,
            )
        )

        categories = []

        for vendor in vendors[:10]:

            categories.append(
                ExpenseCategory(
                    category=vendor.get(
                        "vendor_name",
                        "Unknown",
                    ),
                    amount=float(
                        vendor.get(
                            "amount",
                            0,
                        )
                        or 0
                    ),
                    percentage=float(
                        vendor.get(
                            "pct_of_total",
                            0,
                        )
                        or 0
                    ),
                )
            )

        return FinancialOverviewExpenseBreakdown(
            categories=categories,
        )


financial_overview_expense_breakdown_service = (
    FinancialOverviewExpenseBreakdownService()
)