"""
Tax Calendar Service
Reads tax calendar from database
"""
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import HTTPException, status
import logging
from bson import ObjectId

from app.db import get_collection
from app.models.tax_calendar import TaxCalendar

logger = logging.getLogger(__name__)


class TaxCalendarService:
    """Service for managing tax calendar entries."""

    def __init__(self):
        self.tax_calendar_collection = get_collection("tax_calendar")

    async def get_all_events(self) -> List[Dict[str, Any]]:
        """Get all tax calendar events (shared for all users)."""
        try:
            cursor = self.tax_calendar_collection.find({}).sort("due_date", 1)
            events = await cursor.to_list(length=None)
            
            return [
                {
                    "id": str(e.get("_id", "")),
                    "description": e.get("description"),
                    "due_date": e.get("due_date").isoformat() if isinstance(e.get("due_date"), datetime) else e.get("due_date"),
                    "frequency": e.get("frequency"),
                    "category": e.get("category", "federal"),
                    "notes": e.get("notes"),
                }
                for e in events
            ]
        except Exception as exc:
            logger.error(f"Error fetching tax calendar: {exc}")
            return []

    async def get_upcoming_events(self, days_ahead: int = 60) -> List[Dict[str, Any]]:
        """Get upcoming tax calendar events within specified days."""
        try:
            now = datetime.now(timezone.utc)
            future_date = now.replace(hour=23, minute=59, second=59)
            
            # Add days
            from datetime import timedelta
            future_date = future_date + timedelta(days=days_ahead)
            
            cursor = self.tax_calendar_collection.find(
                {
                    "due_date": {
                        "$gte": now,
                        "$lte": future_date,
                    }
                }
            ).sort("due_date", 1)
            
            events = await cursor.to_list(length=None)
            
            return [
                {
                    "id": str(e.get("_id", "")),
                    "description": e.get("description"),
                    "due_date": e.get("due_date").isoformat() if isinstance(e.get("due_date"), datetime) else e.get("due_date"),
                    "frequency": e.get("frequency"),
                    "category": e.get("category", "federal"),
                    "notes": e.get("notes"),
                }
                for e in events
            ]
        except Exception as exc:
            logger.error(f"Error fetching upcoming tax events: {exc}")
            return []

    async def add_event(
        self,
        description: str,
        due_date: datetime,
        frequency: str,
        category: str = "federal",
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a tax calendar event."""
        try:
            doc = {
                "description": description,
                "due_date": due_date,
                "frequency": frequency,
                "category": category,
                "notes": notes,
            }
            
            result = await self.tax_calendar_collection.insert_one(doc)
            
            return {
                "id": str(result.inserted_id),
                "description": description,
                "due_date": due_date.isoformat(),
                "frequency": frequency,
                "category": category,
                "notes": notes,
            }
        except Exception as exc:
            logger.error(f"Error adding tax calendar event: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add tax calendar event",
            ) from exc

    async def update_event(
        self,
        event_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update a tax calendar event."""
        try:
            result = await self.tax_calendar_collection.update_one(
                {"_id": ObjectId(event_id)},
                {"$set": kwargs},
            )
            
            if result.matched_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tax calendar event not found",
                )
            
            # Return updated event
            event = await self.tax_calendar_collection.find_one({"_id": ObjectId(event_id)})
            return {
                "id": str(event["_id"]),
                "description": event.get("description"),
                "due_date": event.get("due_date").isoformat() if isinstance(event.get("due_date"), datetime) else event.get("due_date"),
                "frequency": event.get("frequency"),
                "category": event.get("category", "federal"),
                "notes": event.get("notes"),
            }
        except Exception as exc:
            logger.error(f"Error updating tax calendar event: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update tax calendar event",
            ) from exc

    async def delete_event(self, event_id: str) -> None:
        """Delete a tax calendar event."""
        try:
            result = await self.tax_calendar_collection.delete_one(
                {"_id": ObjectId(event_id)}
            )
            
            if result.deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tax calendar event not found",
                )
        except Exception as exc:
            logger.error(f"Error deleting tax calendar event: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete tax calendar event",
            ) from exc


tax_calendar_service = TaxCalendarService()
