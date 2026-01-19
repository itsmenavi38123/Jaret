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
    nda_required: bool = False
    beta_notes: Optional[str] = None

class UpdateBetaNotesRequest(BaseModel):
    user_id: str
    beta_notes: Optional[str] = None

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

@router.get("/all-users")
async def get_all_users(current_user: dict = Depends(require_admin_role)):
    try:
        users_collection = get_collection("users")

        # Get all users
        users_cursor = users_collection.find({})
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
                "is_paused": user.get("is_paused", False)
            }
            users_data.append(user_info)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": users_data
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
            "is_paused": user.get("is_paused", False)
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
    limit: int = 100,
    skip: int = 0
):
    try:
        logs = await admin_logs_service.get_logs(limit=limit, skip=skip)

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
                    "limit": limit,
                    "skip": skip,
                    "has_more": len(logs) == limit
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
            "nda_required": request.nda_required,
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
    nda_required: Optional[bool] = None,
    limit: int = 50,
    skip: int = 0
):
    try:
        beta_profiles_collection = get_collection("beta_profiles")

        # Build match conditions
        match_conditions = {"is_beta": True}
        if cohort:
            match_conditions["beta_cohort"] = cohort
        if status:
            match_conditions["beta_status"] = status
        if nda_required is not None:
            match_conditions["nda_required"] = nda_required

        # Aggregation pipeline
        pipeline = [
            {"$match": match_conditions},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$project": {
                "user_id": 1,
                "email": "$user.email",
                "beta_cohort": 1,
                "beta_status": 1,
                "nda_required": 1,
                "beta_notes": 1,
                "beta_updated_at": 1,
                "beta_updated_by": 1
            }},
            {"$skip": skip},
            {"$limit": limit}
        ]

        beta_users_cursor = beta_profiles_collection.aggregate(pipeline)
        beta_users = await beta_users_cursor.to_list(length=None)

        # Get total count
        count_pipeline = [
            {"$match": match_conditions},
            {"$count": "total"}
        ]
        count_result = await beta_profiles_collection.aggregate(count_pipeline).to_list(length=1)
        total = count_result[0]["total"] if count_result else 0

        # Format response
        formatted_users = []
        for user in beta_users:
            formatted_users.append({
                "user_id": user["user_id"],
                "email": user["email"],
                "beta_cohort": user.get("beta_cohort"),
                "beta_status": user.get("beta_status"),
                "nda_required": user.get("nda_required", False),
                "beta_notes": user.get("beta_notes") or None,
                "beta_updated_at": (
                    user.get("beta_updated_at").isoformat()
                    if user.get("beta_updated_at")
                    else None
                ),
                "beta_updated_by": user.get("beta_updated_by")
            })


        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": formatted_users,
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "skip": skip,
                    "has_more": skip + limit < total
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

@router.get("/support/onboarding-stuck")
async def get_onboarding_stuck_users(
    current_user: dict = Depends(require_admin_role),
    days_threshold: int = Query(7, description="Days since last progress to consider stuck")
):
    try:
        users_collection = get_collection("users")
        business_profiles_collection = get_collection("business_profiles")

        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

        # Find verified users without business profiles or with old last_active
        stuck_users = []
        async for user in users_collection.find({
            "is_verified": True,
            "$or": [
                {"last_active": {"$lt": cutoff_date}},
                {"last_active": {"$exists": False}, "created_at": {"$lt": cutoff_date}}
            ]
        }):
            # Check if they have business profile
            has_profile = await business_profiles_collection.count_documents({"user_id": user["_id"]}) > 0
            if not has_profile:
                days_since = (datetime.utcnow() - (user.get("last_active") or user.get("created_at", datetime.utcnow()))).days
                stuck_users.append({
                    "user_id": user["_id"],
                    "email": user.get("email"),
                    "onboarding_state": "no_business_profile",
                    "days_since_last_progress": days_since
                })

        return JSONResponse(
            status_code=200,
            content={"success": True, "data": stuck_users}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/support/verification-failures")
async def get_verification_failures(
    current_user: dict = Depends(require_admin_role)
):
    try:
        users_collection = get_collection("users")
        tokens_collection = get_collection("email_verification_tokens")

        failures = []
        async for user in users_collection.find({"is_verified": False}):
            user_id = user["_id"]
            # Check for expired tokens
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
                failures.append({
                    "user_id": user_id,
                    "email": user.get("email"),
                    "verification_status": "unverified",
                    "last_verification_sent_at": last_sent.get("created_at") if last_sent else None,
                    "failure_reason": "expired"
                })

        return JSONResponse(
            status_code=200,
            content={"success": True, "data": failures}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/support/auth-errors")
async def get_auth_errors(
    current_user: dict = Depends(require_admin_role)
):
    try:
        # For now, return empty as we don't have auth error logs yet
        # In a real implementation, query logs for auth failures
        return JSONResponse(
            status_code=200,
            content={"success": True, "data": []}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/support/token-issues")
async def get_token_issues(
    current_user: dict = Depends(require_admin_role)
):
    try:
        # For now, return empty as we don't have token failure logs yet
        # In a real implementation, query for expired/invalid tokens
        return JSONResponse(
            status_code=200,
            content={"success": True, "data": []}
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

        # Get beta user ids
        beta_users_cursor = users_collection.find({"is_beta": True}, {"_id": 1})
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
                    "average_sessions_per_beta_user": None,
                    "median_session_length": None
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

        # Sessions (not available)
        average_sessions_per_beta_user = None
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
                "median_session_length": median_session_length
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


