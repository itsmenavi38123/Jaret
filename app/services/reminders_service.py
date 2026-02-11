"""
Reminders Service
Generates dynamic reminders from QuickBooks data and tax calendar
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from fastapi import HTTPException, status
import logging

from app.models.reminders import Reminder, TaxCalendarEvent
from app.services.quickbooks_token_service import quickbooks_token_service
from app.services import quickbooks_service
from app.services.quickbooks_service import token_has_expired
from app.services.tax_calendar_service import tax_calendar_service
from app.models.quickbooks.token import QuickBooksToken

logger = logging.getLogger(__name__)


class RemindersService:
    """
    Service for generating dynamic reminders from QuickBooks data.
    Queries invoices, bills, payroll, and tax calendar to create actionable reminders.
    """

    def __init__(self):
        pass

    async def get_dynamic_reminders(
        self,
        user_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate dynamic reminders from QuickBooks data.
        Combines:
        - Overdue invoices
        - Upcoming bill payments
        - Pending payroll
        - Upcoming tax deadlines
        
        Returns sorted reminders (overdue first, then by due date).
        """
        try:
            # Get user's QuickBooks tokens
            tokens = await quickbooks_token_service.get_tokens_by_user(user_id)
            if not tokens:
                logger.warning(f"No QuickBooks token for user {user_id}")
                return []
            
            # Get first active token
            token = next((t for t in tokens if t.is_active), tokens[0])
            
            # Ensure token is valid
            token = await self._ensure_valid_token(token)
            
            reminders: List[Tuple[Reminder, int]] = []  # (reminder, sort_order)
            now = datetime.now(timezone.utc)
            
            # Query invoices for overdue amounts
            invoice_reminders = await self._get_invoice_reminders(token, user_id, now)
            reminders.extend([(r, 0) for r in invoice_reminders])  # Priority 0 (highest)
            
            # Query bills for upcoming payments
            bill_reminders = await self._get_bill_reminders(token, user_id, now)
            reminders.extend([(r, 1) for r in bill_reminders])  # Priority 1
            
            # Query payroll status
            payroll_reminders = await self._get_payroll_reminders(token, user_id, now)
            reminders.extend([(r, 1) for r in payroll_reminders])  # Priority 1
            
            # Query tax calendar
            tax_reminders = await self._get_tax_reminders(user_id, now)
            reminders.extend([(r, 2) for r in tax_reminders])  # Priority 2
            
            # Sort: overdue first (negative days), then by due date
            reminders.sort(
                key=lambda x: (
                    x[1],  # priority order
                    x[0].days_until_due if x[0].days_until_due else 999,  # overdue (negative) first
                    x[0].due_date,  # then by date
                )
            )
            
            # Convert to response format and limit
            result = [r[0].dict() for r in reminders[:limit]]
            return result
            
        except Exception as exc:
            logger.exception(f"Error generating reminders for user {user_id}: {exc}")
            return []

    async def _get_invoice_reminders(
        self,
        token: QuickBooksToken,
        user_id: str,
        now: datetime,
    ) -> List[Reminder]:
        """Query overdue unpaid invoices and create reminders."""
        try:
            endpoint = f"{quickbooks_service.get_api_base_url()}/v3/company/{token.realm_id}/query"
            # Get unpaid invoices (Balance > 0 means unpaid)
            query = "SELECT Id, DocNumber, CustomerRef, DueDate, Balance FROM Invoice WHERE Balance > '0'"
            
            response = await quickbooks_service._perform_qbo_request(
                "GET",
                endpoint,
                token.access_token,
                params={"query": query, "minorversion": "73"},
            )
            
            data = response.json()
            invoices = data.get("QueryResponse", {}).get("Invoice", [])
            
            if not invoices:
                return []
            
            # Filter overdue invoices (due date before today)
            today = now.date()
            overdue_invoices = []
            
            invoice_list = invoices if isinstance(invoices, list) else [invoices]
            for invoice in invoice_list:
                due_date_str = invoice.get("DueDate")
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str).date()
                        if due_date < today:
                            overdue_invoices.append(invoice)
                    except Exception as e:
                        logger.warning(f"Error parsing invoice due date: {e}")
            
            overdue_count = len(overdue_invoices)
            if overdue_count > 0:
                return [
                    Reminder(
                        label=f"Invoice follow-up: {overdue_count} client{'s' if overdue_count != 1 else ''} overdue",
                        due_date=now,
                        action_type="invoice_followup",
                        category="cash",
                        priority="critical",
                        days_until_due=0,  # Already overdue
                        related_entity=f"{overdue_count} invoices",
                    )
                ]
            
            return []
            
        except Exception as exc:
            logger.exception(f"Error querying invoices: {exc}")
            return []
            
            if not invoices:
                return []
            
            # Count overdue invoices
            overdue_count = len(invoices) if isinstance(invoices, list) else (1 if invoices else 0)
            
            if overdue_count > 0:
                return [
                    Reminder(
                        label=f"Invoice follow-up: {overdue_count} client{'s' if overdue_count != 1 else ''} overdue",
                        due_date=now,
                        action_type="invoice_followup",
                        category="cash",
                        priority="critical",
                        days_until_due=0,  # Already overdue
                        related_entity=f"{overdue_count} invoices",
                    )
                ]
            
            return []
            
        except Exception as exc:
            logger.exception(f"Error querying invoices: {exc}")
            return []

    async def _get_bill_reminders(
        self,
        token: QuickBooksToken,
        user_id: str,
        now: datetime,
    ) -> List[Reminder]:
        """Query unpaid bills due in next 7 days and create reminders."""
        try:
            endpoint = f"{quickbooks_service.get_api_base_url()}/v3/company/{token.realm_id}/query"
            # Get unpaid bills (Balance > 0 means unpaid)
            query = "SELECT Id, DocNumber, VendorRef, DueDate, Balance FROM Bill WHERE Balance > '0'"
            
            response = await quickbooks_service._perform_qbo_request(
                "GET",
                endpoint,
                token.access_token,
                params={"query": query, "minorversion": "73"},
            )
            
            data = response.json()
            bills = data.get("QueryResponse", {}).get("Bill", [])
            
            if not bills:
                return []
            
            reminders = []
            today = now.date()
            future_date = (now + timedelta(days=7)).date()
            bill_list = bills if isinstance(bills, list) else [bills]
            
            for bill in bill_list:
                vendor_name = bill.get("VendorRef", {}).get("name", "Vendor")
                due_date_str = bill.get("DueDate")
                
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str).date()
                        # Only include bills due in next 7 days
                        if today <= due_date <= future_date:
                            days_until = (due_date - today).days
                            reminders.append(
                                Reminder(
                                    label=f"{vendor_name} payment due ({datetime.combine(due_date, datetime.min.time()).strftime('%b %d')})",
                                    due_date=datetime.combine(due_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                                    action_type="bill_payment",
                                    category="cash",
                                    priority="high" if days_until <= 2 else "normal",
                                    days_until_due=days_until,
                                    related_entity=vendor_name,
                                )
                            )
                    except Exception as e:
                        logger.warning(f"Error parsing bill due date: {e}")
            
            return reminders
            
        except Exception as exc:
            logger.exception(f"Error querying bills: {exc}")
            return []

    async def _get_payroll_reminders(
        self,
        token: QuickBooksToken,
        user_id: str,
        now: datetime,
    ) -> List[Reminder]:
        """Query pending payroll due in next 14 days."""
        try:
            endpoint = f"{quickbooks_service.get_api_base_url()}/v3/company/{token.realm_id}/query"
            
            # Query active employees - use proper boolean syntax
            query = "SELECT Id, DisplayName FROM Employee WHERE Active = true"
            
            response = await quickbooks_service._perform_qbo_request(
                "GET",
                endpoint,
                token.access_token,
                params={"query": query, "minorversion": "73"},
            )
            
            data = response.json()
            employees = data.get("QueryResponse", {}).get("Employee", [])
            
            if employees:
                # For now, create a generic payroll reminder
                # In a real implementation, you'd check payroll status from QB
                return [
                    Reminder(
                        label="Payroll approval pending",
                        due_date=now + timedelta(days=3),
                        action_type="payroll_approval",
                        category="operations",
                        priority="high",
                        days_until_due=3,
                    )
                ]
            
            return []
            
        except Exception as exc:
            logger.exception(f"Error checking payroll status: {exc}")
            return []

    async def _get_tax_reminders(
        self,
        user_id: str,
        now: datetime,
    ) -> List[Reminder]:
        """Query tax calendar from database and return upcoming tax deadlines."""
        try:
            # Get upcoming tax events from database (next 60 days)
            events = await tax_calendar_service.get_upcoming_events(days_ahead=60)
            
            reminders = []
            for event in events:
                try:
                    due_date_str = event.get("due_date")
                    if isinstance(due_date_str, str):
                        due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    else:
                        due_date = due_date_str
                    
                    if not isinstance(due_date, datetime):
                        continue
                    
                    days_until = (due_date.date() - now.date()).days
                    
                    reminders.append(
                        Reminder(
                            id=event.get("id"),
                            label=f"{event.get('description')} due in {days_until} day{'s' if days_until != 1 else ''}",
                            due_date=due_date,
                            action_type="tax_payment",
                            category="compliance",
                            priority="high" if days_until <= 10 else "normal",
                            days_until_due=days_until,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Error processing tax event: {e}")
                    continue
            
            return reminders
            
        except Exception as exc:
            logger.exception(f"Error querying tax calendar: {exc}")
            return []

    async def _ensure_valid_token(self, token: QuickBooksToken) -> QuickBooksToken:
        """Ensure token is valid, refresh if needed."""
        if token_has_expired(token.created_at, token.expires_in):
            try:
                # Refresh the token using QuickBooks service
                new_token_data = await quickbooks_service.refresh_access_token(token.refresh_token)
                
                # Update the token in database
                from app.models.quickbooks.token import QuickBooksTokenUpdate
                update_data = QuickBooksTokenUpdate(
                    access_token=new_token_data["access_token"],
                    refresh_token=new_token_data.get("refresh_token", token.refresh_token),
                    expires_in=new_token_data.get("expires_in", token.expires_in),
                    x_refresh_token_expires_in=new_token_data.get("x_refresh_token_expires_in", token.x_refresh_token_expires_in),
                    updated_at=datetime.now(timezone.utc),
                )
                
                updated = await quickbooks_token_service.update_token(token.id, update_data)
                return updated or token
            except Exception as exc:
                logger.warning(f"Failed to refresh token: {exc}")
                return token
        
        return token


reminders_service = RemindersService()
