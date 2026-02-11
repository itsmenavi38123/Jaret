"""
Tax Calendar API Routes
Manage user's tax compliance calendar
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.routes.auth.auth import get_current_user
from app.services.tax_calendar_service import tax_calendar_service

router = APIRouter(prefix="/tax-calendar", tags=["tax-calendar"])


class TaxEventCreate(BaseModel):
    """Request to create a tax calendar event."""
    description: str = Field(..., description="Event description")
    due_date: datetime = Field(..., description="When the event is due")
    frequency: str = Field(..., description="Frequency (weekly, monthly, quarterly, annual)")
    category: str = Field(default="federal", description="Category (federal, state, local, payroll)")
    notes: Optional[str] = Field(None, description="Additional notes")


class TaxEventUpdate(BaseModel):
    """Request to update a tax calendar event."""
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    frequency: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def get_tax_calendar(
    current_user: dict = Depends(get_current_user),
):
    """Get all tax calendar events (shared across all users)."""
    try:
        events = await tax_calendar_service.get_all_events()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({"success": True, "data": events}),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tax calendar: {exc}",
        ) from exc


@router.get("/upcoming")
async def get_upcoming_tax_events(
    days: int = 60,
    current_user: dict = Depends(get_current_user),
):
    """Get upcoming tax calendar events within specified days."""
    try:
        events = await tax_calendar_service.get_upcoming_events(days_ahead=days)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({"success": True, "data": events}),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch upcoming tax events: {exc}",
        ) from exc



@router.post("/")
async def create_tax_event(
    body: TaxEventCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new tax calendar event."""
    try:
        event = await tax_calendar_service.add_event(
            user_id=current_user["id"],
            description=body.description,
            due_date=body.due_date,
            frequency=body.frequency,
            category=body.category,
            notes=body.notes,
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder({"success": True, "data": event}),
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tax calendar event: {exc}",
        ) from exc


@router.put("/{event_id}")
async def update_tax_event(
    event_id: str,
    body: TaxEventUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a tax calendar event (admin only)."""
    try:
        # Only update fields that are provided
        update_data = {}
        if body.description is not None:
            update_data["description"] = body.description
        if body.due_date is not None:
            update_data["due_date"] = body.due_date
        if body.frequency is not None:
            update_data["frequency"] = body.frequency
        if body.category is not None:
            update_data["category"] = body.category
        if body.notes is not None:
            update_data["notes"] = body.notes
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        
        event = await tax_calendar_service.update_event(
            event_id=event_id,
            **update_data,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({"success": True, "data": event}),
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tax calendar event: {exc}",
        ) from exc


@router.delete("/{event_id}")
async def delete_tax_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a tax calendar event (admin only)."""
    try:
        await tax_calendar_service.delete_event(
            event_id=event_id,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({"success": True, "message": "Tax calendar event deleted"}),
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tax calendar event: {exc}",
        ) from exc
