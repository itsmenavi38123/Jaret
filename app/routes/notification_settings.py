from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.models.notification_settings import NotificationSettingsRequest
from app.routes.auth.auth import get_current_user
from app.services.notification_settings_service import notification_settings_service

router = APIRouter(tags=["notification_settings"])


@router.get("/")
async def get_notification_settings(current_user: dict = Depends(get_current_user)):
    result = await notification_settings_service.get_settings(
        user_id=current_user["id"],
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": result,
        }),
    )


@router.post("/")
async def save_notification_settings(
    body: NotificationSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    result = await notification_settings_service.save_settings(
        user_id=current_user["id"],
        settings=body,
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": result,
        }),
    )
