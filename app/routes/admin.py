from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Optional
from app.db import get_collection
from datetime import datetime, timedelta
from app.services.system_health_service import system_health_service
import secrets
from uuid import uuid4
from fastapi import Response
import hashlib
from app.services.email_service import send_email
from app.config import _now_utc
from app.routes.admin_auth import require_admin_session
from app.services.admin_logs_service import admin_logs_service, AdminLogCreate
from app.models.beta_profile import BetaProfile, BetaCohort, BetaStatus
from app.models.peer_teaser import PeerTeaser, PeerTeaserCreate, PeerTeaserUpdate
from app.models.dreaming_run import DreamingRun
from app.services.feature_usage_service import feature_usage_service
from app.services.memory_search_service import MemorySearchService
from app.services.customer_memory_service import CustomerMemoryService
from app.services.memory_failure_service import MemoryFailureService
from app.services.admin_memory_service import AdminMemoryService
from app.services.admin_search_service import AdminSearchService
from app.services.memory_export_service import MemoryExportService
from app.services.memory_review_service import MemoryReviewService
from typing import List

memory_export_service = MemoryExportService()
memory_search_service = MemorySearchService()
customer_memory_service = CustomerMemoryService()
memory_failure_service = MemoryFailureService()
admin_memory_service = AdminMemoryService()
admin_search_service = AdminSearchService()
memory_review_service = MemoryReviewService()

async def require_admin_role(current_admin: dict = Depends(require_admin_session)):
    """
    Dependency to ensure the caller holds a valid, unexpired, unrevoked admin
    session (see app.routes.admin_auth) - gated on the dedicated `is_admin`
    flag, not the customer-facing `role` string.
    """
    return current_admin

# Request body models for admin actions
class UserActionRequest(BaseModel):
    user_id: str

class SetBetaRequest(BaseModel):
    user_id: str
    is_beta: bool
    beta_cohort: Optional[BetaCohort] = None
    beta_status: Optional[BetaStatus] = None
    beta_notes: Optional[str] = None

class UpdateBetaNotesRequest(BaseModel):
    user_id: str
    beta_notes: Optional[str] = None

class BetaModeToggleRequest(BaseModel):
    is_beta_mode_enabled: bool

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

@router.get("/dashboard")
async def get_admin_stats(current_user: dict = Depends(require_admin_role)):
    try:
        users_collection = get_collection("users")
        qb_tokens_collection = get_collection("quickbooks_tokens")
        xero_tokens_collection = get_collection("xero_tokens")

        # Total users
        total_users = await users_collection.count_documents({})

        # Total beta users - count users where is_beta is true
        total_beta_users = await users_collection.count_documents({"is_beta": True})

        # Active users last 7 days - users who logged in recently OR signed up recently
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        active_7_days = await users_collection.count_documents({
            "$or": [
                {"last_active": {"$gte": seven_days_ago}},
                {"$and": [
                    {"last_active": {"$exists": False}},
                    {"created_at": {"$gte": seven_days_ago}}
                ]}
            ]
        })

        # Active users last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_30_days = await users_collection.count_documents({
            "$or": [
                {"last_active": {"$gte": thirty_days_ago}},
                {"$and": [
                    {"last_active": {"$exists": False}},
                    {"created_at": {"$gte": thirty_days_ago}}
                ]}
            ]
        })

        # Email verified percentage
        verified_users = await users_collection.count_documents({"is_verified": True})
        email_verified_percent = (verified_users / total_users * 100) if total_users > 0 else 0

        # % completed onboarding - check if user has business_profile
        business_profiles_collection = get_collection("business_profiles")
        onboarded_users = await business_profiles_collection.distinct("user_id")
        onboarded_count = len(onboarded_users)
        onboarding_completed_percent = (onboarded_count / total_users * 100) if total_users > 0 else 0

        # Connected accounting system percentage
        # Users with QB tokens
        qb_users = await qb_tokens_collection.distinct("user_id")
        # Users with Xero tokens
        xero_users = await xero_tokens_collection.distinct("user_id")
        # Unique users with any accounting connection
        connected_users = set(qb_users + xero_users)
        connected_count = len(connected_users)
        connected_percent = (connected_count / total_users * 100) if total_users > 0 else 0

        # System status from health service
        system_status = await system_health_service.get_system_status()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "total_users": total_users,
                    "total_beta_users": total_beta_users,
                    "active_users_7_days": active_7_days,
                    "active_users_30_days": active_30_days,
                    "email_verified_percent": round(email_verified_percent, 2),
                    "onboarding_completed_percent": round(onboarding_completed_percent, 2),
                    "connected_accounting_percent": round(connected_percent, 2),
                    "system_status": system_status
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
            )

@router.post("/beta-mode")
async def set_beta_mode(
    request: BetaModeToggleRequest,
    current_user: dict = Depends(require_admin_role)
):
    try:
        settings_collection = get_collection("system_settings")

        await settings_collection.update_one(
            {"_id": "beta_mode"},
            {
                "$set": {
                    "is_beta_mode_enabled": request.is_beta_mode_enabled,
                    "updated_at": _now_utc(),
                    "updated_by": current_user["id"]
                }
            },
            upsert=True
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Beta mode set to {'ON' if request.is_beta_mode_enabled else 'OFF'}",
                "data": {
                    "is_beta_mode_enabled": request.is_beta_mode_enabled
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/beta-mode")
async def get_beta_mode_status(current_user: dict = Depends(require_admin_role)):
    try:
        settings_collection = get_collection("system_settings")

        setting = await settings_collection.find_one({"_id": "beta_mode"})
        is_beta_mode_enabled = setting.get("is_beta_mode_enabled", False) if setting else False

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "is_beta_mode_enabled": is_beta_mode_enabled
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/all-users")
async def get_all_users(
    current_user: dict = Depends(require_admin_role),
    page: int = 1,
    per_page: int = 20
):
    try:
        users_collection = get_collection("users")

        if page < 1:
            page = 1
        skip = (page - 1) * per_page

        # Get total count
        total_count = await users_collection.count_documents({})
        total_pages = (total_count + per_page - 1) // per_page

        # Get users with pagination
        users_cursor = users_collection.find({}).skip(skip).limit(per_page)
        users = await users_cursor.to_list(length=None)

        users_data = []
        for user in users:
            # Determine account status
            account_status = "invited"  # default

            if user.get("password_hash"):
                if user.get("is_verified", False):
                    # Check if recently active (last 30 days)
                    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                    last_active = user.get("last_active")
                    if last_active and last_active >= thirty_days_ago:
                        account_status = "active"
                    else:
                        account_status = "email_verified"
                else:
                    account_status = "signed_up"
            # TODO: Add "paused" status logic if needed

            # Get role (default to owner, can be extended later)
            role = user.get("role", "Viewer")

            # Get signup source (default to demo, can be extended later)
            signup_source = user.get("signup_source", "demo")

            # Format timestamps
            created_date = user.get("created_at")
            last_login = user.get("last_active")

            user_info = {
                "user_id": user.get("_id"),
                "email": user.get("email"),
                "account_status": account_status,
                "role": role,
                "created_date": created_date.isoformat() if created_date else None,
                "last_login_timestamp": last_login.isoformat() if last_login else None,
                "signup_source": signup_source,
                "is_paused": user.get("is_paused", False),
                "is_beta": user.get("is_beta", False)
            }
            users_data.append(user_info)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": users_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/user/{user_id}")
async def get_single_user(user_id: str, current_user: dict = Depends(require_admin_role)):
    try:
        users_collection = get_collection("users")

        # Get single user by ID
        user = await users_collection.find_one({"_id": user_id})

        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "User not found"}
            )

        # Determine account status
        account_status = "invited"  # default

        if user.get("is_paused", False):
            account_status = "paused"
        elif user.get("password_hash"):
            if user.get("is_verified", False):
                # Check if recently active (last 30 days)
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                last_active = user.get("last_active")
                if last_active and last_active >= thirty_days_ago:
                    account_status = "active"
                else:
                    account_status = "email_verified"
            else:
                account_status = "signed_up"

        # Get role (default to Client)
        role = user.get("role", "Client")

        # Get signup source (default to demo)
        signup_source = user.get("signup_source", "demo")

        # Format timestamps
        created_date = user.get("created_at")
        last_login = user.get("last_active")

        user_info = {
            "user_id": user.get("_id"),
            "email": user.get("email"),
            "account_status": account_status,
            "role": role,
            "created_date": created_date.isoformat() if created_date else None,
            "last_login_timestamp": last_login.isoformat() if last_login else None,
            "signup_source": signup_source,
            "is_paused": user.get("is_paused", False),
            "is_beta": user.get("is_beta", False)
        }

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": user_info
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/user/resend-verification")
async def resend_verification_email(request: UserActionRequest, current_user: dict = Depends(require_admin_role)):
    try:
        user_id = request.user_id
        users_collection = get_collection("users")
        tokens_collection = get_collection("email_verification_tokens")

        # Get user
        user = await users_collection.find_one({"_id": user_id})
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "User not found"}
            )

        # Check if user is already verified
        if user.get("is_verified", False):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "User is already verified"}
            )

        # Check if there's an existing token that's still valid (not expired)
        existing_token = await tokens_collection.find_one({
            "user_id": user_id,
            "used": False,
            "expires_at": {"$gt": _now_utc()}
        })

        if existing_token:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Verification email was recently sent. Please check your inbox or wait before requesting again."}
            )

        # Create new verification token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        await tokens_collection.insert_one({
            "_id": str(uuid4()),
            "user_id": user_id,
            "token_hash": token_hash,
            "used": False,
            "expires_at": _now_utc() + timedelta(minutes=10),  # 10 minutes expiry
            "created_at": _now_utc(),
        })

        # Send verification email
        verify_url = f"https://lightsignal.app/auth/verification?token={raw_token}"
        send_email(
            to_email=user.get("email"),
            subject="Verify your LightSignal account",
            html_content=f"""
            <h2>Verify your LightSignal account</h2>
            <p>Please verify your email to activate your account.</p>
            <a href="{verify_url}"
               style="display:inline-block;padding:12px 18px;
                      background:#2563eb;color:#ffffff;
                      text-decoration:none;border-radius:6px;">
               Verify Email
            </a>
            <p>This link will expire in 10 minutes.</p>
            """
        )

        # Log the admin action
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=user_id,
                target_user_email=user.get("email"),
                action="Resend Verification"
            )
        )

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Verification email sent successfully"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/user/pause")
async def pause_user_account(request: UserActionRequest, current_user: dict = Depends(require_admin_role)):
    try:
        user_id = request.user_id
        users_collection = get_collection("users")

        # Get user
        user = await users_collection.find_one({"_id": user_id})
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "User not found"}
            )

        # Check if user is verified (only verified users can be paused)
        if not user.get("is_verified", False):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Cannot pause unverified account"}
            )

        # Check if already paused
        if user.get("is_paused", False):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Account is already paused"}
            )

        # Pause the account
        await users_collection.update_one(
            {"_id": user_id},
            {"$set": {"is_paused": True}}
        )

        # Log the admin action
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=user_id,
                target_user_email=user.get("email"),
                action="Account Paused"
            )
        )

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Account paused successfully"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/user/unpause")
async def unpause_user_account(request: UserActionRequest, current_user: dict = Depends(require_admin_role)):
    try:
        user_id = request.user_id
        users_collection = get_collection("users")

        # Get user
        user = await users_collection.find_one({"_id": user_id})
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "User not found"}
            )

        # Check if not paused
        if not user.get("is_paused", False):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Account is not paused"}
            )

        # Unpause the account
        await users_collection.update_one(
            {"_id": user_id},
            {"$set": {"is_paused": False}}
        )

        # Log the admin action
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=user_id,
                target_user_email=user.get("email"),
                action="Account Unpaused"
            )
        )

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Account unpaused successfully"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/user/force-logout")
async def force_user_logout(request: UserActionRequest, current_user: dict = Depends(require_admin_role)):
    try:
        user_id = request.user_id
        # For force logout, we'll clear the user's last_active timestamp
        # This will force them to login again on next API call that requires authentication
        users_collection = get_collection("users")

        # Get user
        user = await users_collection.find_one({"_id": user_id})
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "User not found"}
            )

        # Clear last_active to force re-authentication on next request
        await users_collection.update_one(
            {"_id": user_id},
            {"$set": {"last_active": None}}
        )

        # Log the admin action
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=user_id,
                target_user_email=user.get("email"),
                action="Force Logout"
            )
        )

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "User forced logout successfully"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/logs")
async def get_admin_logs(
    current_user: dict = Depends(require_admin_role),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    search: Optional[str] = Query(None, description="Search actions"),
    action_type: Optional[str] = Query(None, description="Filter action types")
):
    try:
        skip = (page - 1) * per_page
        result = await admin_logs_service.get_logs(
            limit=per_page,
            skip=skip,
            search=search,
            action_type=action_type
        )
        logs = result["logs"]
        total_count = result["total_count"]
        total_pages = (total_count + per_page - 1) // per_page

        # Format logs for response
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "id": log.get("_id"),
                "admin_email": log.get("admin_email"),
                "target_user_id": log.get("target_user_id"),
                "target_user_email": log.get("target_user_email"),
                "action": log.get("action"),
                "timestamp": log.get("timestamp").isoformat() if log.get("timestamp") else None,
                "details": log.get("details")
            })

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": formatted_logs,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/user/set-beta")
async def set_user_beta_status(request: SetBetaRequest, current_user: dict = Depends(require_admin_role)):
    try:
        user_id = request.user_id
        users_collection = get_collection("users")
        beta_profiles_collection = get_collection("beta_profiles")

        # Get user
        user = await users_collection.find_one({"_id": user_id})
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "User not found"}
            )

        # Update user's is_beta
        await users_collection.update_one(
            {"_id": user_id},
            {"$set": {"is_beta": request.is_beta}}
        )

        # Update or create beta profile
        beta_profile_data = {
            "user_id": user_id,
            "is_beta": request.is_beta,
            "beta_cohort": request.beta_cohort,
            "beta_status": request.beta_status,
            "beta_notes": request.beta_notes,
            "beta_updated_at": _now_utc(),
            "beta_updated_by": current_user["id"]
        }

        if request.is_beta:
            # If enabling beta, set status to invited if not set
            if not request.beta_status:
                beta_profile_data["beta_status"] = BetaStatus.invited
        else:
            # If revoking, set status to inactive
            beta_profile_data["beta_status"] = BetaStatus.inactive

        await beta_profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": beta_profile_data},
            upsert=True
        )

        # Log the admin action
        action = "Enabled Beta Access" if request.is_beta else "Revoked Beta Access"
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=user_id,
                target_user_email=user.get("email"),
                action=action
            )
        )

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": f"Beta status updated successfully"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/beta-users")
async def get_beta_users(
    current_user: dict = Depends(require_admin_role),
    cohort: Optional[BetaCohort] = None,
    status: Optional[BetaStatus] = None,
    page: int = 1,
    per_page: int = 20
):
    try:
        users_collection = get_collection("users")
        beta_profiles_collection = get_collection("beta_profiles")
        qb_tokens_collection = get_collection("quickbooks_tokens")
        xero_tokens_collection = get_collection("xero_tokens")

        if page < 1:
            page = 1
        skip = (page - 1) * per_page

        # Build match conditions
        match_conditions = {"is_beta": True}

        # Get total count
        total_count = await users_collection.count_documents(match_conditions)
        total_pages = (total_count + per_page - 1) // per_page

        # Get beta users
        beta_users_cursor = users_collection.find(match_conditions).skip(skip).limit(per_page)
        beta_users = await beta_users_cursor.to_list(length=None)

        # Format response with dynamic beta status calculation
        formatted_users = []
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        for user in beta_users:
            user_id = user.get("_id")
            
            # Calculate beta status based on user state
            calculated_status = BetaStatus.invited  # Default
            
            # Check if user is inactive (last 30 days no activity)
            last_active = user.get("last_active")
            if last_active and last_active < thirty_days_ago:
                calculated_status = BetaStatus.inactive
            # Check if accounting connected (QB or Xero)
            elif user_id:
                qb_tokens = await qb_tokens_collection.find_one({"user_id": user_id})
                xero_tokens = await xero_tokens_collection.find_one({"user_id": user_id})
                
                if qb_tokens or xero_tokens:
                    calculated_status = BetaStatus.onboarded
                # Check if verified
                elif user.get("is_verified", False):
                    calculated_status = BetaStatus.accepted
            
            # Apply filter if status parameter is provided
            if status and calculated_status != status:
                continue
            
            formatted_users.append({
                "user_id": user_id,
                "email": user.get("email"),
                "beta_cohort": user.get("beta_cohort"),
                "beta_status": calculated_status,
                "beta_notes": user.get("beta_notes") or None,
                "is_verified": user.get("is_verified", False),
                "last_active": user.get("last_active").isoformat() if user.get("last_active") else None,
                "created_at": user.get("created_at").isoformat() if user.get("created_at") else None
            })

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": formatted_users,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/beta-users/update-beta-notes")
async def update_beta_notes(request: UpdateBetaNotesRequest, current_user: dict = Depends(require_admin_role)):
    try:
        user_id = request.user_id
        beta_notes = request.beta_notes
        users_collection = get_collection("users")
        beta_profiles_collection = get_collection("beta_profiles")

        # Check if user exists and is beta
        user = await users_collection.find_one({"_id": user_id})
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "User not found"}
            )

        if not user.get("is_beta", False):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "User is not a beta user"}
            )

        # Update beta notes
        await beta_profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "beta_notes": beta_notes,
                "beta_updated_at": _now_utc(),
                "beta_updated_by": current_user["id"]
            }}
        )

        # Log the admin action
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=user_id,
                target_user_email=user.get("email"),
                action="Updated Beta Notes"
            )
        )

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Beta notes updated successfully"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/support")
async def get_all_support_issues(
    current_user: dict = Depends(require_admin_role),
    days_threshold: int = Query(7, description="Days since last progress to consider stuck"),
    issue_type: Optional[str] = Query(None, description="Filter by issue_type: onboarding_stuck, verification_failed, auth_error, token_error"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
):
    try:
        users_collection = get_collection("users")
        tokens_collection = get_collection("email_verification_tokens")
        business_profiles_collection = get_collection("business_profiles")
        
        all_issues = []
        
        # 1. Get Onboarding Stuck Users
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
        async for user in users_collection.find({
            "is_verified": True,
            "$or": [
                {"last_active": {"$lt": cutoff_date}},
                {"last_active": {"$exists": False}, "created_at": {"$lt": cutoff_date}}
            ]
        }):
            has_profile = await business_profiles_collection.count_documents({"user_id": user["_id"]}) > 0
            if not has_profile:
                days_since = (datetime.utcnow() - (user.get("last_active") or user.get("created_at", datetime.utcnow()))).days
                issue = {
                    "issue_id": f"onboarding_{user['_id']}",
                    "user_id": user["_id"],
                    "email": user.get("email"),
                    "issue_type": "onboarding_stuck",
                    "severity": "high" if days_since > 30 else "medium",
                    "title": "User Stuck in Onboarding",
                    "description": f"No business profile setup. Last activity: {days_since} days ago",
                    "days_since_last_progress": days_since,
                    "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
                    "last_active": user.get("last_active").isoformat() if user.get("last_active") else None,
                    "metadata": {
                        "is_verified": user.get("is_verified", False),
                        "is_beta": user.get("is_beta", False)
                    }
                }
                if not issue_type or issue_type == "onboarding_stuck":
                    all_issues.append(issue)
        
        # 2. Get Verification Failures
        async for user in users_collection.find({"is_verified": False}):
            user_id = user["_id"]
            expired_tokens = await tokens_collection.count_documents({
                "user_id": user_id,
                "used": False,
                "expires_at": {"$lt": _now_utc()}
            })
            if expired_tokens > 0:
                last_sent = await tokens_collection.find_one(
                    {"user_id": user_id},
                    sort=[("created_at", -1)]
                )
                hours_since = (datetime.utcnow() - (last_sent.get("created_at") if last_sent else datetime.utcnow())).total_seconds() / 3600
                issue = {
                    "issue_id": f"verification_{user_id}",
                    "user_id": user_id,
                    "email": user.get("email"),
                    "issue_type": "verification_failed",
                    "severity": "high",
                    "title": "Email Verification Expired",
                    "description": "Verification token expired. User needs new verification email.",
                    "failure_reason": "expired",
                    "last_verification_sent_at": last_sent.get("created_at").isoformat() if last_sent else None,
                    "hours_since_sent": round(hours_since, 2),
                    "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
                    "metadata": {
                        "is_verified": user.get("is_verified", False),
                        "is_beta": user.get("is_beta", False)
                    }
                }
                if not issue_type or issue_type == "verification_failed":
                    all_issues.append(issue)
        
        # 3. Auth Errors (reserved for future use)
        # Currently empty but structure ready for when auth error logs are available
        if not issue_type or issue_type == "auth_error":
            pass
        
        # 4. Token Issues (reserved for future use)
        # Currently empty but structure ready for when token failure logs are available
        if not issue_type or issue_type == "token_error":
            pass
        
        # Sort by severity (high first) and then by creation date
        severity_order = {"high": 0, "medium": 1, "low": 2}
        all_issues.sort(key=lambda x: (
            severity_order.get(x.get("severity", "low"), 99),
            x.get("created_at", "")
        ))
        
        # Get summary statistics (before pagination)
        issue_summary = {
            "onboarding_stuck": sum(1 for i in all_issues if i["issue_type"] == "onboarding_stuck"),
            "verification_failed": sum(1 for i in all_issues if i["issue_type"] == "verification_failed"),
            "auth_error": 0,  # Reserved
            "token_error": 0   # Reserved
        }
        
        # Apply pagination
        total_count = len(all_issues)
        total_pages = (total_count + per_page - 1) // per_page
        skip = (page - 1) * per_page
        paginated_issues = all_issues[skip:skip + per_page]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "summary": issue_summary,
                "total_issues": total_count,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "data": paginated_issues
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/usage-signals")
async def get_usage_signals(current_user: dict = Depends(require_admin_role)):
    try:
        users_collection = get_collection("users")

        # Get beta user ids (excluding admin users)
        beta_users_cursor = users_collection.find(
            {"is_beta": True, "role": {"$ne": "Admin"}}, 
            {"_id": 1}
        )
        beta_user_ids = [user["_id"] async for user in beta_users_cursor]
        total_beta_users = len(beta_user_ids)

        if total_beta_users == 0:
            return JSONResponse(
                status_code=200,
                content={
                    "total_beta_users": 0,
                    "onboarding_completion_percent": 0,
                    "accounting_connected_percent": 0,
                    "scenario_planning_opened_percent": 0,
                    "insights_viewed_percent": 0,
                    "average_sessions_per_beta_user": 0,
                    "median_session_length": None,
                    "total_login_count": 0
                }
            )

        # Onboarding completion
        business_profiles_collection = get_collection("business_profiles")
        onboarded = await business_profiles_collection.distinct("user_id", {"user_id": {"$in": beta_user_ids}})
        onboarding_completion_percent = round((len(onboarded) / total_beta_users) * 100, 2)

        # Accounting connected
        qb_tokens_collection = get_collection("quickbooks_tokens")
        xero_tokens_collection = get_collection("xero_tokens")
        qb_users = await qb_tokens_collection.distinct("user_id", {"user_id": {"$in": beta_user_ids}})
        xero_users = await xero_tokens_collection.distinct("user_id", {"user_id": {"$in": beta_user_ids}})
        connected_users = set(qb_users + xero_users)
        accounting_connected_percent = round((len(connected_users) / total_beta_users) * 100, 2)

        # Scenario planning opened
        scenario_users = await feature_usage_service.get_unique_users_per_feature("scenario_planning", beta_user_ids)
        scenario_planning_opened_percent = round((scenario_users / total_beta_users) * 100, 2)

        # Insights viewed
        insights_users = await feature_usage_service.get_unique_users_per_feature("insights", beta_user_ids)
        insights_viewed_percent = round((insights_users / total_beta_users) * 100, 2)

        # Sessions and Session Length Calculation
        login_logs_collection = get_collection("login_logs")
        session_lengths = []
        total_sessions = 0
        users_with_logins = 0

        for user_id in beta_user_ids:
            # Get login times for this user
            user_logins_cursor = login_logs_collection.find(
                {"user_id": user_id},
                {"login_time": 1, "_id": 0}
            ).sort("login_time", 1)
            user_logins = [doc["login_time"] async for doc in user_logins_cursor]
            
            if len(user_logins) > 0:
                users_with_logins += 1
                # Count sessions as number of logins
                total_sessions += len(user_logins)
                
                # Only calculate session duration if user has multiple logins
                if len(user_logins) > 1:
                    # Calculate time spent in app per session (time between consecutive logins)
                    # This represents how long between sessions (inactive time)
                    for i in range(len(user_logins) - 1):
                        duration = (user_logins[i+1] - user_logins[i]).total_seconds() / 60  # in minutes
                        if duration > 0:
                            session_lengths.append(duration)

        # Average sessions per beta user (total logins / total beta users)
        average_sessions_per_beta_user = round(total_sessions / total_beta_users, 2) if total_beta_users > 0 else 0

        # Median session interval (time between consecutive logins in minutes)
        # This shows how frequently users return to the app
        if session_lengths:
            session_lengths.sort()
            n = len(session_lengths)
            if n % 2 == 1:
                median_session_length = round(session_lengths[n // 2], 2)
            else:
                median_session_length = round((session_lengths[n // 2 - 1] + session_lengths[n // 2]) / 2, 2)
        else:
            median_session_length = None

        return JSONResponse(
            status_code=200,
            content={
                "total_beta_users": total_beta_users,
                "onboarding_completion_percent": onboarding_completion_percent,
                "accounting_connected_percent": accounting_connected_percent,
                "scenario_planning_opened_percent": scenario_planning_opened_percent,
                "insights_viewed_percent": insights_viewed_percent,
                "average_sessions_per_beta_user": average_sessions_per_beta_user,
                "median_session_length": None
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/health")
async def get_system_health(current_user: dict = Depends(require_admin_role), hours: int = 24):
    """
    Get comprehensive system health metrics for admin dashboard
    """
    try:
        health_data = await system_health_service.get_health_metrics(hours)

        return JSONResponse(
            status_code=200,
            content=health_data
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/memories/search")
async def search_memories(
    query: str,
    user_id: str | None = None,
    observation_type: str | None = None,
    agent_name: str | None = None,
    tag: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: dict = Depends(require_admin_role)
):
    try:

        memories = await admin_search_service.search_memories(
            query=query,
            user_id=user_id,
            observation_type=observation_type,
            agent_name=agent_name,
            tag=tag,
            start_date=start_date,
            end_date=end_date
        )

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "success": True,
                    "data": memories
                }
            )
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.get("/memories/review")
async def review_queue(
    current_user: dict = Depends(require_admin_role)
):
    try:

        memories = await memory_review_service.get_review_queue()

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "success": True,
                    "data": memories
                }
            )
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.get("/memories/export/{user_id}/json")
async def export_memories(
    user_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:

        memories = await memory_export_service.export_customer_memories(
            user_id=user_id
        )

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "success": True,
                    "data": memories
                }
            )
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.get("/memories/export/{user_id}/csv")
async def export_memories_csv(
    user_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:

        csv_data = await memory_export_service.export_customer_memories_csv(
            user_id=user_id
        )

        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition":
                f"attachment; filename=customer_{user_id}_memories.csv"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@router.get("/memories/{user_id}")
async def get_customer_memories(
    user_id: str,
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
    include_outdated: bool = False,
    observation_type: str | None = None,
    agent_name: str | None = None,
    tags: List[str] | None = Query(None),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: dict = Depends(require_admin_role)
):
    try:

        result = await admin_memory_service.get_customer_memories(
            user_id=user_id,
            query=query,
            include_outdated=include_outdated,
            page=page,
            page_size=page_size,
            observation_type=observation_type,
            agent_name=agent_name,
            tags=tags,
            start_date=start_date,
            end_date=end_date
        )

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "success": True,
                    "data": result["memories"],
                    "pagination": result["pagination"]
                }
            )
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.post("/memories/{memory_id}/approve")
async def approve_memory(
    memory_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:

        await memory_review_service.approve_memory(
            memory_id=memory_id
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Memory approved"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.post("/memories/{memory_id}/reject")
async def reject_memory(
    memory_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:

        await memory_review_service.reject_memory(
            memory_id=memory_id
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Memory rejected"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.post("/memories/{memory_id}/pin")
async def pin_memory(
    memory_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:

        await customer_memory_service.pin_memory(
            memory_id=memory_id
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Memory pinned"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.post("/memories/{memory_id}/unpin")
async def unpin_memory(
    memory_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:

        await customer_memory_service.unpin_memory(
            memory_id=memory_id
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Memory unpinned"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:

        await admin_memory_service.soft_delete_memory(
            memory_id=memory_id
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Memory deleted"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@router.get("/memory-failures")
async def get_memory_failures(
    current_user: dict = Depends(require_admin_role)
):
    try:

        cursor = (
            memory_failure_service.failures
            .find({})
            .sort(
                "timestamp",
                -1
            )
            .limit(100)
        )

        failures = [
            failure async for failure in cursor
        ]

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "success": True,
                    "data": failures
                }
            )
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

class BroadcastCreateRequest(BaseModel):
    message: str
    severity: str
    audience: str

@router.post("/broadcast")
async def create_broadcast(
    body: BroadcastCreateRequest,
    current_user: dict = Depends(require_admin_role)
):
    try:
        broadcasts_col = get_collection("broadcasts")
        now = datetime.utcnow()
        doc_id = str(uuid4())
        
        broadcast_doc = {
            "_id": doc_id,
            "message": body.message,
            "severity": body.severity,
            "audience": body.audience,
            "created_at": now,
            "created_by": current_user["id"],
            "dismissed_by": []
        }
        
        await broadcasts_col.insert_one(broadcast_doc)
        
        # Log the admin action
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=None,
                target_user_email=None,
                action=f"Created Broadcast Banner: {body.message[:50]}..."
            )
        )
        
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "data": {
                    "id": broadcast_doc["_id"],
                    "message": broadcast_doc["message"],
                    "severity": broadcast_doc["severity"],
                    "audience": broadcast_doc["audience"],
                    "created_at": now.isoformat(),
                    "created_by": broadcast_doc["created_by"],
                    "dismissed_by": []
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/broadcasts")
async def get_recent_broadcasts(
    current_user: dict = Depends(require_admin_role),
    page: int = 1,
    per_page: int = 10
):
    try:
        broadcasts_col = get_collection("broadcasts")
        users_col = get_collection("users")

        if page < 1:
            page = 1
        skip = (page - 1) * per_page

        # Total non-admin users (used for dismissed_count context)
        total_matching_all = await users_col.count_documents({"role": {"$ne": "Admin"}})

        # Total broadcasts for pagination metadata
        total_count = await broadcasts_col.count_documents({})
        total_pages = (total_count + per_page - 1) // per_page

        # Fetch page, latest first
        cursor = broadcasts_col.find({}).sort("created_at", -1).skip(skip).limit(per_page)
        broadcasts = [doc async for doc in cursor]

        formatted_list = []
        for b in broadcasts:
            dismissed_count = len(b.get("dismissed_by", []))
            formatted_list.append({
                "id": b["_id"],
                "message": b["message"],
                "severity": b["severity"],
                "audience": b["audience"],
                "created_at": b["created_at"].isoformat() if b.get("created_at") else None,
                "dismissed_count": dismissed_count,
                "audience_count": total_matching_all
            })

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": formatted_list,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/shape-gaps")
async def get_shape_gaps(
    current_user: dict = Depends(require_admin_role)
):
    """
    Retrieve all shape gaps (signals fired without a matching layout shape),
    aggregated with frequencies, last fired times, and mapping statuses.
    """
    try:
        shape_gaps_col = get_collection("shape_gaps")

        pipeline = [
            {
                "$group": {
                    "_id": "$signal_id",
                    "count": {"$sum": 1},
                    "last_fired": {"$max": "$timestamp"}
                }
            },
            {"$sort": {"count": -1}},
            {
                "$project": {
                    "signal_id": "$_id",
                    "count": 1,
                    "last_fired": 1,
                    "_id": 0
                }
            }
        ]

        from app.services.signal_shape_mapper import SIGNAL_TO_SHAPE

        cursor = shape_gaps_col.aggregate(pipeline)
        gaps = []
        async for gap in cursor:
            sig_id = gap["signal_id"]
            is_mapped = (sig_id in SIGNAL_TO_SHAPE) or (sig_id in SIGNAL_TO_SHAPE.values())
            
            last_fired_val = gap.get("last_fired")
            last_fired_str = last_fired_val.isoformat() if last_fired_val else None

            gaps.append({
                "signal_id": sig_id,
                "count": gap["count"],
                "last_fired": last_fired_str,
                "is_mapped": is_mapped
            })

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": gaps
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/teasers")
async def get_teasers(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter teasers by status"),
    current_user: dict = Depends(require_admin_role)
):
    try:
        peer_teasers_col = get_collection("peer_teasers")
        query = {}
        if status:
            query["status"] = status
        
        # Count total documents matching query
        total_count = await peer_teasers_col.count_documents(query)
        total_pages = (total_count + per_page - 1) // per_page
        
        skip = (page - 1) * per_page
        cursor = peer_teasers_col.find(query).sort("created_at", -1).skip(skip).limit(per_page)
        teasers = await cursor.to_list(length=None)
        
        users_col = get_collection("users")
        
        # Serialize using Pydantic model to handle proper format/aliases
        serialized_teasers = []
        for teaser_doc in teasers:
            teaser_obj = PeerTeaser.model_validate(teaser_doc)
            
            # Resolve company_name dynamically for source_customer_id
            user_doc = await users_col.find_one({"_id": teaser_obj.source_customer_id})
            company_name = user_doc.get("company_name", "Unknown Business") if user_doc else "Unknown Business"
            
            teaser_dict = teaser_obj.model_dump(by_alias=False)
            teaser_dict["source_business_name"] = company_name
            serialized_teasers.append(teaser_dict)
            
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({
                "success": True,
                "data": serialized_teasers,
                "pagination": {
                    "total_count": total_count,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            })
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/teasers")
async def create_teaser(
    payload: PeerTeaserCreate,
    current_user: dict = Depends(require_admin_role)
):
    try:
        # Create new PeerTeaser instance, validating rules
        teaser_doc = PeerTeaser(
            source_customer_id=payload.source_customer_id,
            verified_anonymized=payload.verified_anonymized,
            status=payload.status or "approved",
            teaser_text=payload.teaser_text,
            onboarding_section=payload.onboarding_section or "Financials",
            proposed_by=payload.proposed_by or "manual"
        )
        
        insert_data = teaser_doc.model_dump(by_alias=True)
        peer_teasers_col = get_collection("peer_teasers")
        await peer_teasers_col.insert_one(insert_data)
        
        # Audit log mutating action
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=payload.source_customer_id,
                action="Create Peer Teaser",
                details=f"Created teaser (id: {teaser_doc.id}, status: {teaser_doc.status}) with content: {teaser_doc.teaser_text[:100]}"
            )
        )
        
        return JSONResponse(
            status_code=201,
            content=jsonable_encoder({
                "success": True,
                "data": teaser_doc.model_dump(by_alias=False)
            })
        )
    except ValueError as val_err:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(val_err)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.put("/teasers/{teaser_id}")
async def update_teaser(
    teaser_id: str,
    payload: PeerTeaserUpdate,
    current_user: dict = Depends(require_admin_role)
):
    try:
        peer_teasers_col = get_collection("peer_teasers")
        existing_teaser = await peer_teasers_col.find_one({"_id": teaser_id})
        if not existing_teaser:
            raise HTTPException(status_code=404, detail="Peer teaser not found")
        
        # Dry-run validation of the update data
        merged_teaser = {**existing_teaser, **payload.model_dump(exclude_unset=True)}
        teaser_obj = PeerTeaser.model_validate(merged_teaser)
        
        update_data = payload.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = _now_utc()
            await peer_teasers_col.update_one({"_id": teaser_id}, {"$set": update_data})
            
            # Audit log mutating action
            await admin_logs_service.log_action(
                AdminLogCreate(
                    admin_user_id=current_user["id"],
                    admin_email=current_user["email"],
                    target_user_id=teaser_obj.source_customer_id,
                    action="Update Peer Teaser",
                    details=f"Updated teaser (id: {teaser_id}). Set fields: {list(update_data.keys())}"
                )
            )
            
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({
                "success": True,
                "data": teaser_obj.model_dump(by_alias=False)
            })
        )
    except HTTPException as http_err:
        raise http_err
    except ValueError as val_err:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(val_err)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.delete("/teasers/{teaser_id}")
async def delete_teaser(
    teaser_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:
        peer_teasers_col = get_collection("peer_teasers")
        existing_teaser = await peer_teasers_col.find_one({"_id": teaser_id})
        if not existing_teaser:
            raise HTTPException(status_code=404, detail="Peer teaser not found")
        
        await peer_teasers_col.delete_one({"_id": teaser_id})
        teaser_obj = PeerTeaser.model_validate(existing_teaser)
        
        # Audit log mutating action
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=teaser_obj.source_customer_id,
                action="Delete Peer Teaser",
                details=f"Deleted teaser (id: {teaser_id})"
            )
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Peer teaser deleted successfully"
            }
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/dreaming")
async def get_dreaming_runs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, description="Items per page"),
    current_user: dict = Depends(require_admin_role)
):
    try:
        dreaming_runs_col = get_collection("dreaming_runs")
        total_count = await dreaming_runs_col.count_documents({})
        total_pages = (total_count + per_page - 1) // per_page
        
        skip = (page - 1) * per_page
        cursor = dreaming_runs_col.find({}).sort("pass_number", -1).skip(skip).limit(per_page)
        runs = await cursor.to_list(length=None)
        
        serialized_runs = []
        for run_doc in runs:
            run_obj = DreamingRun.model_validate(run_doc)
            run_dict = run_obj.model_dump(by_alias=False)
            if "full_log" in run_dict:
                del run_dict["full_log"]
            serialized_runs.append(run_dict)
            
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({
                "success": True,
                "data": serialized_runs,
                "pagination": {
                    "total_count": total_count,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            })
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/dreaming/{pass_id}")
async def get_dreaming_run_detail(
    pass_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:
        dreaming_runs_col = get_collection("dreaming_runs")
        run_doc = await dreaming_runs_col.find_one({"_id": pass_id})
        if not run_doc:
            raise HTTPException(status_code=404, detail="Dreaming run log not found")
            
        run_obj = DreamingRun.model_validate(run_doc)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({
                "success": True,
                "data": run_obj.model_dump(by_alias=False)
            })
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/documents")
async def get_admin_documents(current_user: dict = Depends(require_admin_role)):
    try:
        docs_coll = get_collection("documents_metadata")
        users_col = get_collection("users")
        
        # 1. Extraction Failures: extraction_status: "failed" and deleted_by_owner: {"$ne": True}
        failures_cursor = docs_coll.find({
            "extraction_status": "failed",
            "deleted_by_owner": {"$ne": True}
        }).sort("upload_timestamp", -1)
        failures_docs = await failures_cursor.to_list(length=None)
        
        failures_list = []
        for doc in failures_docs:
            user = await users_col.find_one({"_id": doc["customer_id"]})
            company_name = user.get("company_name", "Unknown Business") if user else "Unknown Business"
            failures_list.append({
                "document_id": doc.get("document_id"),
                "filename": doc.get("original_filename"),
                "business_name": company_name,
                "upload_timestamp": doc.get("upload_timestamp").isoformat() if isinstance(doc.get("upload_timestamp"), datetime) else doc.get("upload_timestamp"),
                "failure_reason": doc.get("failure_reason") or "unreadable scan",
                "owner_notified": doc.get("owner_notified", True)
            })
            
        # 2. Soft-deleted documents: deleted_by_owner: True
        soft_deleted_cursor = docs_coll.find({
            "deleted_by_owner": True
        }).sort("owner_deleted_at", -1)
        soft_deleted_docs = await soft_deleted_cursor.to_list(length=None)
        
        soft_deleted_list = []
        for doc in soft_deleted_docs:
            user = await users_col.find_one({"_id": doc["customer_id"]})
            company_name = user.get("company_name", "Unknown Business") if user else "Unknown Business"
            owner_deleted_at = doc.get("owner_deleted_at")
            owner_deleted_at_str = owner_deleted_at.isoformat() if isinstance(owner_deleted_at, datetime) else owner_deleted_at
            
            soft_deleted_list.append({
                "document_id": doc.get("document_id"),
                "filename": doc.get("original_filename"),
                "business_name": company_name,
                "owner_deleted_at": owner_deleted_at_str,
                "extraction_status": doc.get("extraction_status"),
                "extraction_record_id": doc.get("extraction_record_id")
            })
            
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "extraction_failures": failures_list,
                    "soft_deleted_documents": soft_deleted_list
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/documents/{document_id}/resolve")
async def resolve_document_failure(
    document_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:
        docs_coll = get_collection("documents_metadata")
        doc = await docs_coll.find_one({"document_id": document_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        await docs_coll.update_one(
            {"document_id": document_id},
            {"$set": {"extraction_status": "resolved"}}
        )
        
        # Log admin action
        users_col = get_collection("users")
        user = await users_col.find_one({"_id": doc["customer_id"]})
        user_email = user.get("email") if user else "unknown@customer.com"
        
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=doc["customer_id"],
                target_user_email=user_email,
                action="Resolve document extraction failure",
                details=f"Resolved DIA failure for document: {doc.get('original_filename')}"
            )
        )
        
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Document failure marked as resolved"}
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.delete("/documents/{document_id}")
async def hard_delete_document(
    document_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:
        docs_coll = get_collection("documents_metadata")
        ext_coll = get_collection("extraction_records")
        
        doc = await docs_coll.find_one({"document_id": document_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        from app.db import get_gridfs_bucket
        bucket = get_gridfs_bucket()
        
        deleted_fids = set()
        for field in ("original_file_id", "working_file_id"):
            file_id = doc.get(field)
            if file_id and file_id not in deleted_fids:
                try:
                    await bucket.delete(file_id)
                    deleted_fids.add(file_id)
                except Exception as e:
                    print(f"Error deleting GridFS file {file_id}: {e}")
                    
        await docs_coll.delete_one({"document_id": document_id})
        await ext_coll.delete_many({"document_id": document_id})
        
        # Log admin action
        users_col = get_collection("users")
        user = await users_col.find_one({"_id": doc["customer_id"]})
        user_email = user.get("email") if user else "unknown@customer.com"
        
        await admin_logs_service.log_action(
            AdminLogCreate(
                admin_user_id=current_user["id"],
                admin_email=current_user["email"],
                target_user_id=doc["customer_id"],
                target_user_email=user_email,
                action="Hard delete document",
                details=f"Hard-deleted document: {doc.get('original_filename')}"
            )
        )
        
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": f"Document {doc.get('original_filename')} hard-deleted successfully"}
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/documents/{document_id}/extraction")
async def get_admin_document_extraction(
    document_id: str,
    current_user: dict = Depends(require_admin_role)
):
    try:
        docs_coll = get_collection("documents_metadata")
        doc = await docs_coll.find_one({"document_id": document_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        ext_coll = get_collection("extraction_records")
        ext_record = await ext_coll.find_one({"document_id": document_id})
        if not ext_record:
            raise HTTPException(status_code=404, detail="Extraction record not found")
            
        fields = []
        for field in ext_record.get("written_fields", []):
            target = field.get("target") or ""
            clean = target.replace("[]", "").replace("_", " ")
            acronyms = {"ein", "id", "ssn", "us", "dba"}
            display_name = " ".join(w.upper() if w.lower() in acronyms else w.capitalize() for w in clean.split())
            
            edited = field.get("edited", False)
            current_value = field.get("edited_value") if edited else field.get("value")
            
            fields.append({
                "key": target,
                "display_name": display_name,
                "current_value": current_value,
                "edited": edited
            })
            
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "document_id": document_id,
                    "doc_type": doc.get("doc_type") or ext_record.get("doc_type_detected"),
                    "extraction_status": doc.get("extraction_status"),
                    "owner_corrected": doc.get("owner_corrected", False),
                    "fields": fields
                }
            }
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/documents/{document_id}/download")
async def get_admin_document_download(
    document_id: str,
    version: str = "working",
    current_user: dict = Depends(require_admin_role)
):
    if version not in ("working", "original"):
        raise HTTPException(status_code=400, detail="Invalid version parameter. Must be 'working' or 'original'.")
        
    try:
        docs_coll = get_collection("documents_metadata")
        meta = await docs_coll.find_one({"document_id": document_id})
        if not meta:
            raise HTTPException(status_code=404, detail="Document not found")
            
        if version == "original":
            file_id = meta.get("original_file_id")
            fmt = meta.get("original_format")
            filename = meta.get("original_filename", "document")
        else:
            file_id = meta.get("working_file_id") or meta.get("original_file_id")
            fmt = meta.get("working_format") or meta.get("original_format") or "bin"
            filename = meta.get("original_filename", "document")
            if fmt == "pdf" and not filename.lower().endswith(".pdf"):
                base, _ = os.path.splitext(filename)
                filename = f"{base}.pdf"
                
        if not file_id:
            raise HTTPException(status_code=404, detail="No file found for this document")
            
        from app.db import get_gridfs_bucket
        from bson.objectid import ObjectId
        import io
        bucket = get_gridfs_bucket()
        
        if isinstance(file_id, str):
            file_id = ObjectId(file_id)
            
        grid_out = await bucket.open_download_stream(file_id)
        content = await grid_out.read()
        
        mime_mapping = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
            "txt": "text/plain",
            "md": "text/markdown",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        media_type = mime_mapping.get(fmt.lower(), "application/octet-stream")
        
        import os
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")




