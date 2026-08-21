from pydantic import BaseModel
from typing import List


class ExpenseCategory(BaseModel):
    category: str
    amount: float
    percentage: float


class FinancialOverviewExpenseBreakdown(BaseModel):
    total_amount: float = 0.0
    categories: List[ExpenseCategory]
