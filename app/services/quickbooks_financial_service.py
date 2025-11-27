from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import HTTPException, status

from app.models.quickbooks.token import QuickBooksToken, QuickBooksTokenUpdate
from app.services import quickbooks_service
from app.services.quickbooks_service import QuickBooksUnauthorizedError, token_has_expired
from app.services.quickbooks_token_service import quickbooks_token_service


@dataclass
class ProfitAndLossSnapshot:
    total_income: float = 0.0
    cogs: float = 0.0
    gross_profit: float = 0.0
    operating_expenses: float = 0.0
    net_income: float = 0.0
    interest_expense: float = 0.0


@dataclass
class BalanceSheetSnapshot:
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    total_liabilities: float = 0.0
    total_equity: float = 0.0
    cash: float = 0.0
    accounts_receivable: float = 0.0
    accounts_payable: float = 0.0
    inventory: float = 0.0


@dataclass
class CashFlowSnapshot:
    net_cash_operating: float = 0.0
    net_cash_investing: float = 0.0
    net_cash_financing: float = 0.0
    net_change_cash: float = 0.0


def _parse_money(value: Optional[str]) -> float:
    if value is None:
        return 0.0
    value = value.replace(",", "").strip()
    if value in {"", "-"}:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _iter_rows(rows: Optional[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    if not rows:
        return []
    row_items = rows.get("Row") if isinstance(rows, dict) else rows
    if not row_items:
        return []
    return row_items


def _extract_section_total(report: Dict[str, Any], section_names: Iterable[str]) -> float:
    target_names = set(section_names)

    def _walk(row: Dict[str, Any]) -> Optional[float]:
        row_type = row.get("RowType")
        if row_type == "Section":
            header = row.get("Header", {}).get("ColData", [])
            label = header[0].get("value") if header else None
            if label in target_names:
                summary = row.get("Summary", {}).get("ColData", [])
                if len(summary) > 1:
                    return _parse_money(summary[1].get("value"))
            for child in _iter_rows(row.get("Rows")):
                result = _walk(child)
                if result is not None:
                    return result
        elif row_type == "Data":
            # Some totals appear as standalone data rows
            cols = row.get("ColData", [])
            if cols and cols[0].get("value") in target_names and len(cols) > 1:
                return _parse_money(cols[1].get("value"))
        return None

    for root in _iter_rows(report.get("Rows")):
        val = _walk(root)
        if val is not None:
            return val
    return 0.0


def _extract_line_value(report: Dict[str, Any], line_names: Iterable[str]) -> float:
    target_names = set(line_names)

    def _walk(row: Dict[str, Any]) -> Optional[float]:
        row_type = row.get("RowType")
        if row_type == "Data":
            cols = row.get("ColData", [])
            if cols and cols[0].get("value") in target_names and len(cols) > 1:
                return _parse_money(cols[1].get("value"))
        for child in _iter_rows(row.get("Rows")):
            result = _walk(child)
            if result is not None:
                return result
        return None

    for root in _iter_rows(report.get("Rows")):
        val = _walk(root)
        if val is not None:
            return val
    return 0.0

def qb_extract_section_total(report: Dict[str, Any], section_names: Iterable[str]) -> float:
    target_names = set(section_names)

    def _walk(row: Dict[str, Any]) -> Optional[float]:
        row_type = row.get("RowType") or row.get("type")

        if row_type == "Section":
            # Check summary first (QuickBooks stores totals here)
            summary = row.get("Summary", {}).get("ColData", [])
            if summary and summary[0].get("value") in target_names:
                if len(summary) > 1:
                    return _parse_money(summary[1].get("value"))

            # Walk children
            for child in _iter_rows(row.get("Rows")):
                result = _walk(child)
                if result is not None:
                    return result

        elif row_type == "Data":
            # Some totals may appear as Data rows
            cols = row.get("ColData", [])
            if cols and cols[0].get("value") in target_names and len(cols) > 1:
                return _parse_money(cols[1].get("value"))

        return None

    for root in _iter_rows(report.get("Rows")):
        val = _walk(root)
        if val is not None:
            return val
    return 0.0

def _profit_and_loss_from_report(report: Dict[str, Any]) -> ProfitAndLossSnapshot:
    return ProfitAndLossSnapshot(
        total_income=qb_extract_section_total(report, {"Total Income", "Total Revenue"}),
        cogs=qb_extract_section_total(report, {"Total Cost of Goods Sold", "Total Cost of Sales"}),
        gross_profit=qb_extract_section_total(report, {"Gross Profit"}),
        operating_expenses=qb_extract_section_total(report, {"Total Operating Expenses", "Operating Expenses"}),
        net_income=qb_extract_section_total(report, {"Net Income"}),
        interest_expense=_extract_line_value(
            report,
            {
                "Interest Expense",
                "Total Interest Expense",
                "Interest Paid",
            },
        ),
    )


def _balance_sheet_from_report(report: Dict[str, Any]) -> BalanceSheetSnapshot:
    return BalanceSheetSnapshot(
        current_assets=_extract_section_total(report, {"Total Current Assets"}),
        current_liabilities=_extract_section_total(report, {"Total Current Liabilities"}),
        total_liabilities=_extract_section_total(report, {"Total Liabilities"}),
        total_equity=_extract_section_total(report, {"Total Equity"}),
        cash=_extract_section_total(
            report,
            {
                "Cash and Cash Equivalents",
                "Cash and cash equivalents",
                "Cash and Cash Equivalents (Bank Accounts)",
            },
        ),
        accounts_receivable=_extract_line_value(report, {"Accounts Receivable", "Accounts receivable"}),
        accounts_payable=_extract_line_value(report, {"Accounts Payable", "Accounts payable"}),
        inventory=_extract_line_value(report, {"Inventory Asset", "Inventory"}),
    )


def _cashflow_from_report(report: Dict[str, Any]) -> CashFlowSnapshot:
    return CashFlowSnapshot(
        net_cash_operating=_extract_section_total(
            report,
            {"Net Cash Provided by Operating Activities", "Net Cash from Operating Activities"},
        ),
        net_cash_investing=_extract_section_total(
            report,
            {"Net Cash Provided by Investing Activities", "Net Cash from Investing Activities"},
        ),
        net_cash_financing=_extract_section_total(
            report,
            {"Net Cash Provided by Financing Activities", "Net Cash from Financing Activities"},
        ),
        net_change_cash=_extract_section_total(
            report,
            {"Net Change in Cash", "Net cash increase for period"},
        ),
    )


def _days_between(start: date, end: date) -> int:
    return max((end - start).days or 1, 1)


def _fiscal_year_start(today: date) -> date:
    # Quick heuristic: assume fiscal year aligns with calendar year
    return date(today.year, 1, 1)


def _safe_divide(numerator: float, denominator: float) -> Optional[float]:
    if denominator in (0, None):
        return None
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return None


class QuickBooksFinancialService:

    async def get_financial_overview(self, user_id: str) -> Dict[str, Any]:

        realm_id = await self.get_realm_id_by_user(user_id)
        token = await quickbooks_token_service.get_token_by_user_and_realm(user_id, realm_id)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active QuickBooks connection found for realm {realm_id}",
            )

        token = await self._ensure_valid_token(token)

        today = datetime.now(timezone.utc).date()
        profit_params, detail_params, cashflow_params, meta = self._build_period_params(today)
        print(profit_params, detail_params, cashflow_params, meta)

        profit_snapshots, monthly_series, token = await self._fetch_profit_and_loss_reports(
            token, realm_id, profit_params, detail_params
        )
        balance_sheet_report, token = await self._fetch_balance_sheet(token, realm_id)
        cashflow_reports, _ = await self._fetch_cashflow_reports(token, realm_id, cashflow_params)

        overview = self._build_financial_overview(
            today=today,
            profit_reports=profit_snapshots,
            monthly_series=monthly_series,
            meta=meta,
            balance_sheet_report=balance_sheet_report,
            cashflow_reports=cashflow_reports,
        )

        return overview

    async def get_realm_id_by_user(self, user_id: str) -> str:
        tokens = await quickbooks_token_service.get_tokens_by_user(user_id)
        active_tokens = [t for t in tokens if t.is_active]
        if not active_tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active QuickBooks connection found for user",
            )
        return active_tokens[0].realm_id

    async def get_dashboard_kpis(self, user_id: str) -> Dict[str, Any]:
        realm_id = await self.get_realm_id_by_user(user_id)
        token = await quickbooks_token_service.get_token_by_user_and_realm(user_id, realm_id)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active QuickBooks connection found for realm {realm_id}",
            )

        token = await self._ensure_valid_token(token)

        today = datetime.now(timezone.utc).date()
        first_of_month = today.replace(day=1)

        # Fetch MTD Profit and Loss
        mtd_params = {
            "start_date": first_of_month.isoformat(),
            "end_date": today.isoformat(),
        }
        mtd_report, token = await self._call_report_with_refresh(
            token, realm_id, report_name="ProfitAndLoss", params={"accounting_method": "Accrual", **mtd_params}
        )
        print(mtd_report,"=======")
        mtd_snapshot = _profit_and_loss_from_report(mtd_report)
        print(mtd_snapshot)

        # Fetch Balance Sheet for Cash
        balance_sheet_report, token = await self._fetch_balance_sheet(token, realm_id)

        # Fetch Cash Flow for MTD and last month to calculate runway
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        cashflow_params = {
            "mtd": {
                "start_date": first_of_month.isoformat(),
                "end_date": today.isoformat(),
            },
            "last_month": {
                "start_date": last_month_start.isoformat(),
                "end_date": last_month_end.isoformat(),
            },
        }
        cashflow_reports, _ = await self._fetch_cashflow_reports(token, realm_id, cashflow_params)

        # Compute KPIs
        revenue_mtd = round(mtd_snapshot.total_income, 2)
        net_margin_pct = _safe_divide(mtd_snapshot.net_income, mtd_snapshot.total_income)
        net_margin_pct = round(net_margin_pct, 4) if net_margin_pct is not None else None
        cash = round(balance_sheet_report.cash, 2)

        # Calculate runway
        cashflow_mtd_snapshot = cashflow_reports.get("mtd", CashFlowSnapshot())
        cashflow_last_month_snapshot = cashflow_reports.get("last_month", CashFlowSnapshot())
        cash_flow_mtd = cashflow_mtd_snapshot.net_cash_operating or cashflow_mtd_snapshot.net_change_cash
        burn_rate_monthly = abs(
            min(cashflow_last_month_snapshot.net_cash_operating or cashflow_last_month_snapshot.net_change_cash, 0)
        )
        runway_months = _safe_divide(cash, burn_rate_monthly) if burn_rate_monthly else None
        runway_months = round(runway_months, 2) if runway_months is not None else None

        return {
            "revenue_mtd": revenue_mtd,
            "net_margin_pct": net_margin_pct,
            "cash": cash,
            "runway_months": runway_months,
        }

    async def _ensure_valid_token(self, token: QuickBooksToken, *, force_refresh: bool = False) -> QuickBooksToken:
        issued_at = token.updated_at or token.created_at
        if force_refresh or token_has_expired(issued_at, token.expires_in):
            token = await self._refresh_and_update_token(token)
        return token

    async def _refresh_and_update_token(self, token: QuickBooksToken) -> QuickBooksToken:
        refreshed = await quickbooks_service.refresh_access_token(token.refresh_token)
        now = datetime.utcnow()

        update_payload = QuickBooksTokenUpdate(
            access_token=refreshed["access_token"],
            refresh_token=refreshed.get("refresh_token", token.refresh_token),
            expires_in=refreshed.get("expires_in", token.expires_in),
            x_refresh_token_expires_in=refreshed.get("x_refresh_token_expires_in", token.x_refresh_token_expires_in),
            id_token=refreshed.get("id_token", token.id_token),
            updated_at=now,
        )

        updated = await quickbooks_token_service.update_token(token.id, update_payload)
        if not updated:
            # Fall back to returning a derived token object if persistence failed
            updated = token.model_copy(
                update={
                    "access_token": update_payload.access_token,
                    "refresh_token": update_payload.refresh_token or token.refresh_token,
                    "expires_in": update_payload.expires_in or token.expires_in,
                    "x_refresh_token_expires_in": update_payload.x_refresh_token_expires_in or token.x_refresh_token_expires_in,
                    "id_token": update_payload.id_token or token.id_token,
                    "updated_at": now,
                }
            )
        return updated

    async def _fetch_profit_and_loss_reports(
        self,
        token: QuickBooksToken,
        realm_id: str,
        summary_params: Dict[str, Dict[str, str]],
        detail_params: Dict[str, Dict[str, str]],
    ) -> Tuple[Dict[str, ProfitAndLossSnapshot], List[Tuple[str, float]], QuickBooksToken]:
        reports: Dict[str, ProfitAndLossSnapshot] = {}
        token_ref = token
        for key, params in summary_params.items():
            report, token_ref = await self._call_report_with_refresh(
                token_ref,
                realm_id,
                report_name="ProfitAndLoss",
                params={"accounting_method": "Accrual", **params},
            )
            reports[key] = _profit_and_loss_from_report(report)

        monthly_series: List[Tuple[str, float]] = []
        for params in detail_params.values():
            report, token_ref = await self._call_report_with_refresh(
                token_ref,
                realm_id,
                report_name="ProfitAndLoss",
                params={"accounting_method": "Accrual", **params},
            )
            monthly_series = self._parse_monthly_series(report)
        return reports, monthly_series, token_ref

    async def _fetch_balance_sheet(self, token: QuickBooksToken, realm_id: str) -> Tuple[BalanceSheetSnapshot, QuickBooksToken]:
        report, token_ref = await self._call_report_with_refresh(
            token,
            realm_id,
            report_name="BalanceSheet",
            params={"accounting_method": "Accrual", "date_macro": "Today"},
        )
        return _balance_sheet_from_report(report), token_ref

    async def _fetch_cashflow_reports(
        self,
        token: QuickBooksToken,
        realm_id: str,
        cashflow_params: Dict[str, Dict[str, str]],
    ) -> Tuple[Dict[str, CashFlowSnapshot], QuickBooksToken]:
        relevant_keys = ("mtd", "last_month", "custom_last_3_months")
        reports: Dict[str, CashFlowSnapshot] = {}
        token_ref = token
        for key in relevant_keys:
            params = cashflow_params.get(key)
            if not params:
                continue
            report, token_ref = await self._call_report_with_refresh(
                token_ref,
                realm_id,
                report_name="CashFlow",
                params={"accounting_method": "Accrual", **params},
            )
            reports[key] = _cashflow_from_report(report)
        return reports, token_ref

    async def _call_report_with_refresh(
        self,
        token: QuickBooksToken,
        realm_id: str,
        *,
        report_name: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], QuickBooksToken]:
        try:
            report = await quickbooks_service.fetch_report(token.access_token, realm_id, report_name, params)
            return report, token
        except QuickBooksUnauthorizedError:
            refreshed_token = await self._refresh_and_update_token(token)
            report = await quickbooks_service.fetch_report(refreshed_token.access_token, realm_id, report_name, params)
            return report, refreshed_token

    def _build_period_params(
        self, today: date
    ) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]], Dict[str, Dict[str, str]], Dict[str, Any]]:
        first_of_month = today.replace(day=1)
        fiscal_start = _fiscal_year_start(today)
        fiscal_days = _days_between(fiscal_start, today) + 1

        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        quarter_start = date(today.year, quarter_start_month, 1)

        profit_params: Dict[str, Dict[str, str]] = {
            "mtd": {
                "start_date": first_of_month.isoformat(),
                "end_date": today.isoformat(),
            },
            "qtd": {
                "start_date": quarter_start.isoformat(),
                "end_date": today.isoformat(),
            },
            "ytd": {
                "start_date": fiscal_start.isoformat(),
                "end_date": today.isoformat(),
            },
        }

        # Last full month range
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        profit_params["last_month"] = {
            "start_date": last_month_start.isoformat(),
            "end_date": last_month_end.isoformat(),
        }

        # Last 3 full months
        month_ranges: List[Tuple[date, date]] = []
        cursor = first_of_month
        for _ in range(3):
            end = cursor - timedelta(days=1)
            start = end.replace(day=1)
            month_ranges.append((start, end))
            cursor = start
        month_ranges.reverse()

        detail_params: Dict[str, Dict[str, str]] = {
            "last_three_months_detail": {
                "start_date": month_ranges[0][0].isoformat(),
                "end_date": month_ranges[-1][1].isoformat(),
                "columns": "month",
            }
        }

        cashflow_params: Dict[str, Dict[str, str]] = {
            "mtd": {
                "start_date": first_of_month.isoformat(),
                "end_date": today.isoformat(),
            },
            "last_month": {
                "start_date": last_month_start.isoformat(),
                "end_date": last_month_end.isoformat(),
            },
            "custom_last_3_months": {
                "start_date": month_ranges[0][0].isoformat(),
                "end_date": month_ranges[-1][1].isoformat(),
            },
        }

        meta: Dict[str, Any] = {
            "fiscal_days": fiscal_days,
            "month_labels": [rng[0].strftime("%b") for rng in month_ranges],
        }

        return profit_params, detail_params, cashflow_params, meta

    def _build_financial_overview(
        self,
        *,
        today: date,
        profit_reports: Dict[str, ProfitAndLossSnapshot],
        monthly_series: List[Tuple[str, float]],
        meta: Dict[str, Any],
        balance_sheet_report: BalanceSheetSnapshot,
        cashflow_reports: Dict[str, CashFlowSnapshot],
    ) -> Dict[str, Any]:
        mtd = profit_reports.get("mtd", ProfitAndLossSnapshot())
        qtd = profit_reports.get("qtd", ProfitAndLossSnapshot())
        ytd = profit_reports.get("ytd", ProfitAndLossSnapshot())
        last_month = profit_reports.get("last_month", ProfitAndLossSnapshot())

        current_assets = balance_sheet_report.current_assets or 0.0
        current_liabilities = balance_sheet_report.current_liabilities or 0.0
        inventory = balance_sheet_report.inventory or 0.0
        accounts_receivable = balance_sheet_report.accounts_receivable or 0.0
        accounts_payable = balance_sheet_report.accounts_payable or 0.0
        cash = balance_sheet_report.cash or 0.0

        fiscal_start = _fiscal_year_start(today)
        fiscal_days = int(meta.get("fiscal_days") or (_days_between(fiscal_start, today) + 1))
        revenue_per_day = _safe_divide(ytd.total_income, fiscal_days)
        cogs_per_day = _safe_divide(ytd.cogs, fiscal_days)

        dso = _safe_divide(accounts_receivable, revenue_per_day) if revenue_per_day else None
        dpo = _safe_divide(accounts_payable, cogs_per_day) if cogs_per_day else None
        inventory_turns = _safe_divide(ytd.cogs * 12 / max(today.month, 1), inventory) if inventory else None
        if inventory and ytd.cogs:
            inventory_turns = _safe_divide(ytd.cogs, inventory) or inventory_turns
        dio = _safe_divide(365, inventory_turns) if inventory_turns else None
        ccc = (dso or 0) + (dio or 0) - (dpo or 0) if any(v is not None for v in (dso, dpo, dio)) else None

        gross_margin_pct = _safe_divide(mtd.gross_profit, mtd.total_income)
        opex_ratio_pct = _safe_divide(mtd.operating_expenses, mtd.total_income)
        net_margin_pct = _safe_divide(mtd.net_income, mtd.total_income)

        quick_assets = current_assets - inventory
        quick_ratio = _safe_divide(quick_assets, current_liabilities)
        current_ratio = _safe_divide(current_assets, current_liabilities)
        debt_to_equity = _safe_divide(balance_sheet_report.total_liabilities, balance_sheet_report.total_equity)

        operating_income = mtd.gross_profit - mtd.operating_expenses
        interest_cover = _safe_divide(operating_income, max(mtd.interest_expense, 0.0001))

        cashflow_mtd_snapshot = cashflow_reports.get("mtd", CashFlowSnapshot())
        cashflow_last_month_snapshot = cashflow_reports.get("last_month", CashFlowSnapshot())

        cash_flow_mtd = cashflow_mtd_snapshot.net_cash_operating or cashflow_mtd_snapshot.net_change_cash
        burn_rate_monthly = abs(
            min(cashflow_last_month_snapshot.net_cash_operating or cashflow_last_month_snapshot.net_change_cash, 0)
        )
        runway_months = _safe_divide(cash, burn_rate_monthly) if burn_rate_monthly else None

        forecast_series = self._build_forecast(monthly_series)
        net_trend = self._trend_label(monthly_series)

        variance_entries = self._build_variance_entries(mtd, last_month)
        insights = self._build_insights(mtd, last_month, gross_margin_pct, quick_ratio, inventory_turns)
        risks = self._build_risks(gross_margin_pct, quick_ratio, runway_months, ccc)

        computed_metrics = [
            gross_margin_pct,
            opex_ratio_pct,
            net_margin_pct,
            current_ratio,
            quick_ratio,
            debt_to_equity,
            interest_cover,
            dso,
            dpo,
            inventory_turns,
            dio,
            ccc,
            cash_flow_mtd,
            burn_rate_monthly,
            runway_months,
        ]
        available_metric_count = len([m for m in computed_metrics if m is not None])
        ai_confidence_pct = min(0.5 + 0.03 * available_metric_count, 0.95)

        # Calculate EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)
        # EBITDA = Net Income + Interest + Taxes + Depreciation + Amortization
        # For simplicity, we'll use: EBITDA ≈ Operating Income + Depreciation/Amortization
        # Since we don't have D&A separately, we'll use: EBITDA ≈ Gross Profit - Operating Expenses + Interest
        ebitda = operating_income + mtd.interest_expense
        
        # Calculate debt service (for DSCR calculation)
        # Debt service typically includes principal + interest payments
        # We'll use interest expense as a proxy since principal payments aren't in P&L
        debt_service = mtd.interest_expense
        
        # Calculate average monthly expenses for burn rate
        # Monthly expenses = Operating Expenses + Interest
        monthly_expenses_mtd = mtd.operating_expenses + mtd.interest_expense
        
        overview: Dict[str, Any] = {
            "kpis": {
                "revenue_mtd": round(mtd.total_income, 2),
                "revenue_qtd": round(qtd.total_income, 2),
                "revenue_ytd": round(ytd.total_income, 2),
                "gross_margin_pct": round(gross_margin_pct, 4) if gross_margin_pct is not None else None,
                "opex_ratio_pct": round(opex_ratio_pct, 4) if opex_ratio_pct is not None else None,
                "net_margin_pct": round(net_margin_pct, 4) if net_margin_pct is not None else None,
                "cash_flow_mtd": round(cash_flow_mtd, 2) if cash_flow_mtd is not None else None,
                "runway_months": round(runway_months, 2) if runway_months is not None else None,
                "ai_confidence_pct": round(ai_confidence_pct, 2),
                "industry_notes": self._build_industry_notes(gross_margin_pct, net_margin_pct),
            },
            "calculation_values": {
                # Values for: Gross Margin = (Revenue − COGS) / Revenue
                "revenue": round(mtd.total_income, 2),
                "cogs": round(mtd.cogs, 2),
                
                # Values for: OpEx % = OpEx / Revenue
                "opex": round(mtd.operating_expenses, 2),
                
                # Values for: Current Ratio = CA / CL
                "current_assets": round(current_assets, 2),
                "current_liabilities": round(current_liabilities, 2),
                
                # Values for: Quick Ratio = (Cash + AR) / CL
                "cash": round(cash, 2),
                "accounts_receivable": round(accounts_receivable, 2),
                
                # Values for: DSCR = EBITDA / DebtService
                "ebitda": round(ebitda, 2),
                "debt_service": round(debt_service, 2),
                
                # Values for: Burn Rate = Avg(Monthly Expenses − Revenue)
                "monthly_expenses": round(monthly_expenses_mtd, 2),
                "monthly_revenue": round(mtd.total_income, 2),
                
                # Additional useful values
                "gross_profit": round(mtd.gross_profit, 2),
                "net_income": round(mtd.net_income, 2),
                "operating_income": round(operating_income, 2),
                "interest_expense": round(mtd.interest_expense, 2),
            },
            "insights": insights,
            "liquidity": {
                "current_ratio": round(current_ratio, 2) if current_ratio is not None else None,
                "quick_ratio": round(quick_ratio, 2) if quick_ratio is not None else None,
                "dte": round(debt_to_equity, 2) if debt_to_equity is not None else None,
                "interest_cover": round(interest_cover, 2) if interest_cover is not None else None,
            },
            "efficiency": {
                "dso_days": round(dso, 1) if dso is not None else None,
                "dpo_days": round(dpo, 1) if dpo is not None else None,
                "inv_turns": round(inventory_turns, 2) if inventory_turns is not None else None,
                "ccc_days": round(ccc, 1) if ccc is not None else None,
            },
            "cashflow": {
                "burn_rate_monthly": round(burn_rate_monthly, 2) if burn_rate_monthly is not None else None,
                "runway_months": round(runway_months, 2) if runway_months is not None else None,
                "forecast": forecast_series,
                "net_trend_3mo": net_trend,
            },
            "variance": variance_entries,
            "risks": risks,
        }
        
        # Debug: Verify calculation_values is in the response
        print("DEBUG: Overview keys:", list(overview.keys()))
        print("DEBUG: calculation_values present:", "calculation_values" in overview)
        if "calculation_values" in overview:
            print("DEBUG: calculation_values keys:", list(overview["calculation_values"].keys()))
        
        return overview

    def _parse_monthly_series(self, report: Dict[str, Any]) -> List[Tuple[str, float]]:
        columns = report.get("Columns", {}).get("Column", [])
        month_labels = [col.get("ColTitle") or col.get("ColType") for col in columns[1:]]

        def _find_net_income(row: Dict[str, Any]) -> Optional[List[float]]:
            row_type = row.get("RowType")
            if row_type == "Data":
                cols = row.get("ColData", [])
                if cols and cols[0].get("value") == "Net Income":
                    return [_parse_money(col.get("value")) for col in cols[1:]]
            for child in _iter_rows(row.get("Rows")):
                result = _find_net_income(child)
                if result is not None:
                    return result
            return None

        net_income_values: List[float] = []
        for root in _iter_rows(report.get("Rows")):
            result = _find_net_income(root)
            if result is not None:
                net_income_values = result
                break

        # Ensure alignment between labels and values
        series: List[Tuple[str, float]] = []
        for idx, label in enumerate(month_labels):
            value = net_income_values[idx] if idx < len(net_income_values) else 0.0
            series.append((label or f"Month-{idx+1}", value))
        return series

    def _build_forecast(self, monthly_series: List[Tuple[str, float]]) -> List[Dict[str, Any]]:
        values = [value for _, value in monthly_series if isinstance(value, (int, float))]
        if not values:
            return []

        avg_value = mean(values)
        forecast: List[Dict[str, Any]] = []
        for idx in range(1, 4):
            base = avg_value
            best = base * 1.2
            worst = base * 0.8
            forecast.append(
                {
                    "month": f"+{idx}",
                    "base": round(base, 2),
                    "best": round(best, 2),
                    "worst": round(worst, 2),
                }
            )
        return forecast

    def _trend_label(self, monthly_series: List[Tuple[str, float]]) -> str:
        values = [value for _, value in monthly_series if isinstance(value, (int, float))]
        if len(values) < 2:
            return "insufficient-data"
        if values[-1] > values[0] * 1.05:
            return "positive"
        if values[-1] < values[0] * 0.95:
            return "negative"
        return "flat"

    def _build_variance_entries(
        self,
        current: ProfitAndLossSnapshot,
        previous: ProfitAndLossSnapshot,
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        mapping = [
            ("Revenue", current.total_income, previous.total_income),
            ("COGS", current.cogs, previous.cogs),
            ("Expenses", current.operating_expenses, previous.operating_expenses),
            ("Net Profit", current.net_income, previous.net_income),
        ]
        for metric, actual, base in mapping:
            if base in (None, 0):
                variance_pct = None
            else:
                variance_pct = (actual - base) / base if base else None
            entries.append(
                {
                    "metric": metric,
                    "actual": round(actual, 2) if actual is not None else None,
                    "forecast": round(base, 2) if base is not None else None,
                    "variance_pct": round(variance_pct, 3) if variance_pct is not None else None,
                }
            )
        return entries

    def _build_insights(
        self,
        current: ProfitAndLossSnapshot,
        previous: ProfitAndLossSnapshot,
        gross_margin_pct: Optional[float],
        quick_ratio: Optional[float],
        inventory_turns: Optional[float],
    ) -> List[str]:
        insights: List[str] = []
        if gross_margin_pct is not None and previous.total_income:
            prev_margin = _safe_divide(previous.gross_profit, previous.total_income) or 0.0
            delta = (gross_margin_pct - prev_margin) * 100
            if abs(delta) >= 0.5:
                direction = "improved" if delta > 0 else "declined"
                insights.append(f"Gross margin {direction} {abs(delta):.1f}% versus last month.")

        if quick_ratio is not None:
            if quick_ratio < 1:
                insights.append("Quick ratio below 1.0; cash buffer is thin.")
            elif quick_ratio > 2:
                insights.append("Quick ratio above 2.0; short-term liquidity is strong.")

        if inventory_turns is not None:
            if inventory_turns < 4:
                insights.append("Inventory turns lag peers; review stock efficiency.")
            else:
                insights.append("Inventory turnover is healthy relative to typical benchmarks.")

        if not insights:
            insights.append("Financial trends stable this period.")
        return insights

    def _build_risks(
        self,
        gross_margin_pct: Optional[float],
        quick_ratio: Optional[float],
        runway_months: Optional[float],
        ccc: Optional[float],
    ) -> List[Dict[str, Any]]:
        risks: List[Dict[str, Any]] = []

        if gross_margin_pct is not None and gross_margin_pct < 0.3:
            risks.append(
                {
                    "title": "Margin pressure",
                    "note": "Gross margin has dipped below 30%.",
                    "mitigation": "Review pricing and cost drivers.",
                    "confidence_pct": 0.7,
                    "percentile": 40,
                }
            )

        if quick_ratio is not None and quick_ratio < 1:
            risks.append(
                {
                    "title": "Liquidity warning",
                    "note": "Quick ratio under 1.0 limits short-term flexibility.",
                    "mitigation": "Build cash reserves or extend payables.",
                    "confidence_pct": 0.75,
                    "percentile": 45,
                }
            )

        if runway_months is not None and runway_months < 6:
            risks.append(
                {
                    "title": "Runway tight",
                    "note": f"Cash runway projected at {runway_months:.1f} months.",
                    "mitigation": "Moderate spending or raise capital to extend runway.",
                    "confidence_pct": 0.68,
                    "percentile": 50,
                }
            )

        if ccc is not None and ccc > 70:
            risks.append(
                {
                    "title": "Cash conversion drag",
                    "note": "Cash conversion cycle exceeds 70 days.",
                    "mitigation": "Accelerate AR collection and optimize inventory.",
                    "confidence_pct": 0.64,
                    "percentile": 55,
                }
            )

        return risks

    def _build_industry_notes(
        self,
        gross_margin_pct: Optional[float],
        net_margin_pct: Optional[float],
    ) -> List[str]:
        notes: List[str] = []
        if gross_margin_pct is not None:
            margin_pct = gross_margin_pct * 100
            if margin_pct >= 40:
                notes.append("Gross margin trends ahead of typical industry peers.")
            elif margin_pct <= 25:
                notes.append("Gross margin trails industry midpoint; monitor cost structure closely.")

        if net_margin_pct is not None:
            net_pct = net_margin_pct * 100
            if net_pct >= 15:
                notes.append("Net profitability ranks in the top quartile for comparable companies.")
            elif net_pct <= 5:
                notes.append("Net margin under 5%; consider expense optimization.")

        if not notes:
            notes.append("Performance is within standard industry bands.")
        return notes

    async def get_historical_sales(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        granularity: str = "daily"
    ) -> List[Dict[str, Any]]:
        """
        Get historical sales data for demand forecasting.
        
        Args:
            user_id: User ID
            start_date: Start date for historical data
            end_date: End date for historical data
            granularity: Data granularity (daily, weekly, monthly)
        
        Returns:
            List of sales data points
        """
        realm_id = await self.get_realm_id_by_user(user_id)
        token = await quickbooks_token_service.get_token_by_user_and_realm(user_id, realm_id)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active QuickBooks connection found for realm {realm_id}",
            )
        
        token = await self._ensure_valid_token(token)
        
        # Determine column parameter based on granularity
        column_param = {
            "daily": "day",
            "weekly": "week",
            "monthly": "month"
        }.get(granularity, "day")
        
        # Fetch P&L report with time columns
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "columns": column_param,
            "accounting_method": "Accrual"
        }
        
        report, _ = await self._call_report_with_refresh(
            token,
            realm_id,
            report_name="ProfitAndLoss",
            params=params
        )
        
        # Parse time-series revenue data
        sales_data = self._parse_revenue_time_series(report, granularity)
        
        return sales_data
    
    def _parse_revenue_time_series(
        self,
        report: Dict[str, Any],
        granularity: str
    ) -> List[Dict[str, Any]]:
        """Parse revenue time-series from P&L report"""
        columns = report.get("Columns", {}).get("Column", [])
        time_labels = [col.get("ColTitle") or col.get("ColType") for col in columns[1:]]
        
        def _find_revenue(row: Dict[str, Any]) -> Optional[List[float]]:
            row_type = row.get("RowType")
            if row_type == "Section":
                header = row.get("Header", {}).get("ColData", [])
                label = header[0].get("value") if header else None
                if label in {"Total Income", "Total Revenue"}:
                    summary = row.get("Summary", {}).get("ColData", [])
                    return [_parse_money(col.get("value")) for col in summary[1:]]
            
            for child in _iter_rows(row.get("Rows")):
                result = _find_revenue(child)
                if result is not None:
                    return result
            return None
        
        revenue_values: List[float] = []
        for root in _iter_rows(report.get("Rows")):
            result = _find_revenue(root)
            if result is not None:
                revenue_values = result
                break
        
        # Build sales data array
        sales_data: List[Dict[str, Any]] = []
        for idx, label in enumerate(time_labels):
            value = revenue_values[idx] if idx < len(revenue_values) else 0.0
            sales_data.append({
                "period": label or f"Period-{idx+1}",
                "revenue": round(value, 2),
                "granularity": granularity
            })
        
        return sales_data
    
    async def get_product_level_sales(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get product/service-level sales data.
        
        Args:
            user_id: User ID
            start_date: Start date
            end_date: End date
        
        Returns:
            List of product-level sales data
        """
        realm_id = await self.get_realm_id_by_user(user_id)
        token = await quickbooks_token_service.get_token_by_user_and_realm(user_id, realm_id)
        if not token:
            return []
        
        token = await self._ensure_valid_token(token)
        
        # Fetch P&L by Product/Service (if available)
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "accounting_method": "Accrual",
            "group_by": "Product/Service"
        }
        
        try:
            report, _ = await self._call_report_with_refresh(
                token,
                realm_id,
                report_name="ProfitAndLoss",
                params=params
            )
            
            # Parse product-level data
            product_data = self._parse_product_sales(report)
            return product_data
        
        except Exception as e:
            print(f"Error fetching product-level sales: {e}")
            return []
    
    def _parse_product_sales(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse product/service-level sales from report"""
        product_sales: List[Dict[str, Any]] = []
        
        def _walk_products(row: Dict[str, Any]) -> None:
            row_type = row.get("RowType")
            
            if row_type == "Data":
                cols = row.get("ColData", [])
                if len(cols) >= 2:
                    product_name = cols[0].get("value", "")
                    revenue = _parse_money(cols[1].get("value"))
                    
                    if product_name and revenue > 0:
                        product_sales.append({
                            "product_name": product_name,
                            "revenue": round(revenue, 2)
                        })
            
            # Recursively walk children
            for child in _iter_rows(row.get("Rows")):
                _walk_products(child)
        
        for root in _iter_rows(report.get("Rows")):
            _walk_products(root)
        
        return product_sales


quickbooks_financial_service = QuickBooksFinancialService()

