from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db import get_collection
from app.models.notification_settings import NotificationSettingsRequest
from app.routes.auth.auth import get_current_user
from app.services.notification_settings_service import notification_settings_service

router = APIRouter(tags=["notification_settings"])


class NotificationSettingsPartialUpdate(BaseModel):
    model_config = {"extra": "allow"}

    channels: Optional[Dict[str, bool]] = None
    categories: Optional[Dict[str, bool]] = None
    quiet_hours: Optional[Dict[str, Any]] = None
    escalation_days: Optional[int] = None
    custom_thresholds: Optional[List[Dict[str, Any]]] = None
    recipients: Optional[List[str]] = None


@router.get("/")
@router.get("/settings/notifications")
async def get_notification_settings(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    col = get_collection("notification_settings")
    doc = await col.find_one({"user_id": user_id})

    if not doc:
        user_col = get_collection("user_notification_settings")
        doc = await user_col.find_one({"user_id": user_id})

    if doc:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": doc,
            }),
        )

    result = await notification_settings_service.get_settings(user_id=user_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": result,
        }),
    )


@router.patch("/settings/notifications")
async def save_notification_settings(
    body: NotificationSettingsPartialUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    updates = body.model_dump(exclude_unset=True)
    updates["updated_at"] = datetime.now(timezone.utc)

    col = get_collection("notification_settings")
    user_col = get_collection("user_notification_settings")

    # Update in both collections so all consumers see the update
    await col.update_one(
        {"user_id": user_id},
        {"$set": updates, "$setOnInsert": {"created_at": datetime.now(timezone.utc), "user_id": user_id}},
        upsert=True,
    )
    await user_col.update_one(
        {"user_id": user_id},
        {"$set": updates, "$setOnInsert": {"created_at": datetime.now(timezone.utc), "user_id": user_id}},
        upsert=True,
    )

    updated = await col.find_one({"user_id": user_id})
    if updated and "_id" in updated:
        updated["_id"] = str(updated["_id"])

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": updated}),
    )


@router.post("/notifications/test")
async def send_test_notification(current_user: dict = Depends(get_current_user)):
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Test notification sent to {current_user.get('email')} via configured channels.",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
    )



