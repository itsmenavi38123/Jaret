from pydantic import BaseModel
from typing import List


class ExpenseCategory(BaseModel):
    category: str
    amount: float
    percentage: float


class FinancialOverviewExpenseBreakdown(BaseModel):
    categories: List[ExpenseCategory]