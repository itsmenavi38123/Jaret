from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.db import get_collection
from datetime import datetime, timedelta
from app.services.system_health_service import system_health_service
import secrets
from uuid import uuid4
import hashlib
from app.services.email_service import send_email
from app.config import _now_utc
from app.routes.auth.auth import get_current_user
from app.services.admin_logs_service import admin_logs_service, AdminLogCreate
from app.models.beta_profile import BetaProfile, BetaCohort, BetaStatus
from app.services.feature_usage_service import feature_usage_service

async def require_admin_role(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure user has Admin or Owner role"""
    users_collection = get_collection("users")
    user_doc = await users_collection.find_one({"_id": current_user["id"]})

    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    user_role = user_doc.get("role", "Client")
    if user_role not in ["Admin", "Owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user

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
    page: int = 1,
    per_page: int = 20
):
    try:
        if page < 1:
            page = 1
        skip = (page - 1) * per_page
        result = await admin_logs_service.get_logs(limit=per_page, skip=skip)
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
