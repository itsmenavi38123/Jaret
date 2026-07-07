from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.db import get_collection
from app.routes.admin_auth import require_admin_session
from app.config import _now_utc

router = APIRouter(tags=["settings"])

# 1. Public endpoint to check landing page mode
@router.get("/settings/landing-mode")
async def get_landing_mode():
    settings_col = get_collection("settings")
    config = await settings_col.find_one({"_id": "site_config"})
    landing_mode = config.get("landing_mode", "waitlist") if config else "waitlist"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "landing_mode": landing_mode
        }
    )

# 2. Admin endpoint to view landing page mode
@router.get("/admin/settings/landing-mode")
async def admin_get_landing_mode(current_admin: dict = Depends(require_admin_session)):
    settings_col = get_collection("settings")
    config = await settings_col.find_one({"_id": "site_config"})
    landing_mode = config.get("landing_mode", "waitlist") if config else "waitlist"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "landing_mode": landing_mode
        }
    )

# 3. Admin endpoint to toggle landing page mode (No body needed)
@router.put("/admin/settings/landing-mode")
async def admin_toggle_landing_mode(
    current_admin: dict = Depends(require_admin_session)
):
    settings_col = get_collection("settings")
    config = await settings_col.find_one({"_id": "site_config"})
    current_mode = config.get("landing_mode", "waitlist") if config else "waitlist"
    
    new_mode = "trial" if current_mode == "waitlist" else "waitlist"
    
    await settings_col.update_one(
        {"_id": "site_config"},
        {
            "$set": {
                "landing_mode": new_mode,
                "updated_at": _now_utc()
            }
        },
        upsert=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Landing page mode updated to {new_mode}"
        }
    )

from app.routes.auth.auth import get_current_user

@router.get("/broadcasts/active")
async def get_active_broadcast(
    current_user: dict = Depends(get_current_user)
):
    try:
        broadcasts_col = get_collection("broadcasts")
        user_id = current_user["id"]
        
        # Always fetch the absolute latest broadcast only
        # If user dismissed it — return nothing. Older ones never surface.
        latest_broadcast = await broadcasts_col.find_one(
            {},
            sort=[("created_at", -1)]
        )

        if not latest_broadcast:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "data": None}
            )

        # If the user already dismissed this latest broadcast — nothing to show
        if user_id in latest_broadcast.get("dismissed_by", []):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "data": None}
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "id": latest_broadcast["_id"],
                    "message": latest_broadcast["message"],
                    "severity": latest_broadcast["severity"]
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

@router.post("/broadcasts/{id}/dismiss")
async def dismiss_broadcast(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        broadcasts_col = get_collection("broadcasts")
        user_id = current_user["id"]
        
        await broadcasts_col.update_one(
            {"_id": id},
            {"$addToSet": {"dismissed_by": user_id}}
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": "Broadcast dismissed"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

