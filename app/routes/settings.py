from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.db import get_collection
from app.routes.admin_auth import require_admin_session
from app.routes.auth.auth import get_current_user, check_demo_write_guard
from app.config import _now_utc
from app.services.settings_v2_service import settings_v2_service

router = APIRouter(tags=["settings"])


# ------------------------------------------------------------------------------
# Pydantic Models for Partial (PATCH/PUT) Updates
# ------------------------------------------------------------------------------
class GeneralSettingsUpdateRequest(BaseModel):
    timezone: Optional[str] = None
    base_currency: Optional[str] = None
    reporting_period: Optional[str] = None
    demo_mode: Optional[bool] = None
    reduce_motion: Optional[bool] = None


class PhotoPermissionsModel(BaseModel):
    enabled: Optional[bool] = True
    sources: Optional[List[str]] = Field(default_factory=lambda: ["google", "website", "facebook"])


class PrivacySettingsUpdateRequest(BaseModel):
    peer_benchmarking: Optional[bool] = None
    anonymized_ai_use: Optional[bool] = None
    retention_days: Optional[int] = None
    photo_permissions: Optional[PhotoPermissionsModel] = None


class TeamInviteRequest(BaseModel):
    email: str
    role: str = Field(default="Manager", description="Owner, Manager, Bookkeeper")


class ShareLinkCreateRequest(BaseModel):
    scope: str = Field(default="fo+bh", description="Scope of share link e.g. fo+bh")


def _get_user_id(current_user: Any) -> str:
    if isinstance(current_user, dict):
        return current_user.get("id") or current_user.get("_id") or ""
    return str(current_user)


# ------------------------------------------------------------------------------
# 1. GENERAL SETTINGS (GET / PATCH)
# ------------------------------------------------------------------------------
@router.get("/settings/general")
async def get_general_settings(current_user: Any = Depends(get_current_user)):
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.get_general_settings(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.patch("/settings/general")
async def update_general_settings(
    body: GeneralSettingsUpdateRequest,
    current_user: Any = Depends(get_current_user),
):
    check_demo_write_guard(current_user)
    user_id = _get_user_id(current_user)
    updates = body.model_dump(exclude_unset=True)
    data = await settings_v2_service.update_general_settings(user_id, updates)
    return JSONResponse(status_code=200, content={"success": True, "data": data})



@router.get("/diagnostics/export")
async def export_diagnostics(current_user: Any = Depends(get_current_user)):
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.export_diagnostics(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


# ------------------------------------------------------------------------------
# 2. DATA & PRIVACY & PHOTO PERMISSIONS (GET / PATCH)
# ------------------------------------------------------------------------------
@router.get("/settings/privacy")
async def get_privacy_settings(current_user: Any = Depends(get_current_user)):
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.get_privacy_settings(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.patch("/settings/privacy")
async def update_privacy_settings(
    body: PrivacySettingsUpdateRequest,
    current_user: Any = Depends(get_current_user),
):
    check_demo_write_guard(current_user)
    user_id = _get_user_id(current_user)
    updates = body.model_dump(exclude_unset=True)
    data = await settings_v2_service.update_privacy_settings(user_id, updates)
    return JSONResponse(status_code=200, content={"success": True, "data": data})



@router.get("/consents")
async def get_consent_history(current_user: Any = Depends(get_current_user)):
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.get_consent_history(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.post("/account/delete")
async def initiate_account_deletion(current_user: Any = Depends(get_current_user)):
    check_demo_write_guard(current_user)
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.initiate_account_deletion(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


# ------------------------------------------------------------------------------
# 3. SECURITY & TEAM & ADVISOR SHARE LINK
# ------------------------------------------------------------------------------
@router.get("/sessions")
async def get_sessions(current_user: Any = Depends(get_current_user)):
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.get_sessions(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(current_user: Any = Depends(get_current_user)):
    check_demo_write_guard(current_user)
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.revoke_all_sessions(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, current_user: Any = Depends(get_current_user)):
    check_demo_write_guard(current_user)
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.revoke_session(user_id, session_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.get("/team")
async def get_team_members(current_user: Any = Depends(get_current_user)):
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.get_team_members(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.post("/team/invite")
async def invite_team_member(
    body: TeamInviteRequest,
    current_user: dict = Depends(get_current_user),
):
    check_demo_write_guard(current_user)
    data = await settings_v2_service.invite_team_member(current_user["id"], body.email, body.role)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.delete("/team/{member_id}")
async def delete_team_member(member_id: str, current_user: dict = Depends(get_current_user)):
    check_demo_write_guard(current_user)
    data = await settings_v2_service.delete_team_member(current_user["id"], member_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})



@router.post("/share-links")
async def create_share_link(
    body: Optional[ShareLinkCreateRequest] = None,
    current_user: dict = Depends(get_current_user),
):
    check_demo_write_guard(current_user)
    scope = body.scope if body else "fo+bh"
    data = await settings_v2_service.create_share_link(current_user["id"], scope)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.get("/share-links/{link_id}/pdf")
async def download_advisor_pdf(link_id: str, current_user: dict = Depends(get_current_user)):
    dummy_pdf_content = b"%PDF-1.4 Mock Banker Snapshot PDF content"
    return Response(
        content=dummy_pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Banker_Snapshot_{link_id}.pdf"'}
    )


# ------------------------------------------------------------------------------
# 4. AI & CORRECTIONS LEDGER
# ------------------------------------------------------------------------------
@router.get("/corrections")
async def get_corrections(current_user: dict = Depends(get_current_user)):
    data = await settings_v2_service.get_corrections(current_user["id"])
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.post("/corrections/{correction_id}/undo")
async def undo_correction(correction_id: str, current_user: dict = Depends(get_current_user)):
    check_demo_write_guard(current_user)
    data = await settings_v2_service.undo_correction(current_user["id"], correction_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.get("/living-summary")
async def get_living_summary(current_user: dict = Depends(get_current_user)):
    data = await settings_v2_service.get_living_summary(current_user["id"])
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.post("/classifier/run")
async def rerun_classifier(current_user: dict = Depends(get_current_user)):
    data = await settings_v2_service.rerun_classifier(current_user["id"])
    return JSONResponse(status_code=200, content={"success": True, "data": data})


# ------------------------------------------------------------------------------
# 5. BILLING SECTION
# ------------------------------------------------------------------------------
@router.get("/billing/summary")
async def get_billing_summary(current_user: dict = Depends(get_current_user)):
    data = await settings_v2_service.get_billing_summary(current_user["id"])
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.get("/billing/portal")
async def get_billing_portal(current_user: dict = Depends(get_current_user)):
    data = await settings_v2_service.get_billing_portal_url(current_user["id"])
    return JSONResponse(status_code=200, content={"success": True, "data": data})


@router.get("/billing/invoices")
async def get_billing_invoices(current_user: dict = Depends(get_current_user)):
    data = await settings_v2_service.get_billing_invoices(current_user["id"])
    return JSONResponse(status_code=200, content={"success": True, "data": data})


# ------------------------------------------------------------------------------
# 6. BACKUP & UNIFIED SNAPSHOTS
# ------------------------------------------------------------------------------
@router.post("/backup/export")
async def export_backup(format: str = Query("json", description="json or csv"), current_user: dict = Depends(get_current_user)):
    content_str = '{"backup": "data", "status": "clean"}' if format == "json" else "metric,value\nrevenue,50000"
    media_type = "application/json" if format == "json" else "text/csv"
    ext = "json" if format == "json" else "csv"
    return Response(
        content=content_str,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="lightsignal_backup.{ext}"'}
    )


@router.get("/snapshots/unified")
async def get_unified_snapshots(current_user: Any = Depends(get_current_user)):
    user_id = _get_user_id(current_user)
    data = await settings_v2_service.get_unified_snapshots(user_id)
    return JSONResponse(status_code=200, content={"success": True, "data": data})


# ------------------------------------------------------------------------------
# EXISTING LANDING & BROADCAST ROUTES
# ------------------------------------------------------------------------------
@router.get("/settings/landing-mode")
async def get_landing_mode():
    settings_col = get_collection("settings")
    config = await settings_col.find_one({"_id": "site_config"})
    landing_mode = config.get("landing_mode", "waitlist") if config else "waitlist"
    return JSONResponse(status_code=200, content={"success": True, "landing_mode": landing_mode})


@router.get("/admin/settings/landing-mode")
async def admin_get_landing_mode(current_admin: dict = Depends(require_admin_session)):
    settings_col = get_collection("settings")
    config = await settings_col.find_one({"_id": "site_config"})
    landing_mode = config.get("landing_mode", "waitlist") if config else "waitlist"
    return JSONResponse(status_code=200, content={"success": True, "landing_mode": landing_mode})


@router.put("/admin/settings/landing-mode")
async def admin_toggle_landing_mode(current_admin: dict = Depends(require_admin_session)):
    settings_col = get_collection("settings")
    config = await settings_col.find_one({"_id": "site_config"})
    current_mode = config.get("landing_mode", "waitlist") if config else "waitlist"
    new_mode = "trial" if current_mode == "waitlist" else "waitlist"

    await settings_col.update_one(
        {"_id": "site_config"},
        {"$set": {"landing_mode": new_mode, "updated_at": _now_utc()}},
        upsert=True
    )
    return JSONResponse(status_code=200, content={"success": True, "message": f"Landing page mode updated to {new_mode}"})


@router.get("/broadcasts/active")
async def get_active_broadcast(current_user: Any = Depends(get_current_user)):
    try:
        broadcasts_col = get_collection("broadcasts")
        user_id = _get_user_id(current_user)
        latest_broadcast = await broadcasts_col.find_one(
            {"$or": [{"target_user_ids": user_id}, {"target_user_ids": {"$exists": False}}]},
            sort=[("created_at", -1)]
        )
        if not latest_broadcast or user_id in latest_broadcast.get("dismissed_by", []):
            return JSONResponse(status_code=200, content={"success": True, "data": None})

        return JSONResponse(
            status_code=200,
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
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/broadcasts/{id}/dismiss")
async def dismiss_broadcast(id: str, current_user: dict = Depends(get_current_user)):
    check_demo_write_guard(current_user)
    try:
        broadcasts_col = get_collection("broadcasts")
        user_id = current_user["id"]
        await broadcasts_col.update_one({"_id": id}, {"$addToSet": {"dismissed_by": user_id}})
        return JSONResponse(status_code=200, content={"success": True, "message": "Broadcast dismissed"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
