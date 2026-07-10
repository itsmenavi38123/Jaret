import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from app.config import JWT_SECRET, JWT_ALGORITHM, create_access_token, create_refresh_token, _now_utc, settings
import hashlib

from app.db import get_collection
from app.services.quickbooks_token_service import quickbooks_token_service
from app.services.xero_token_service import xero_token_service

import secrets
from app.services.email_service import send_email
from datetime import timezone

router = APIRouter(tags=["auth"])
api_router = APIRouter(tags=["auth"])

from app.services.stripe_service import StripeService

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _prehash(password: str) -> bytes:
    """
    Pre-hash arbitrary-length password with SHA-256 and return raw bytes.
    This ensures bcrypt always receives a fixed-length input (32 bytes).
    """
    return hashlib.sha256(password.encode("utf-8")).digest()

def hash_password(password: str) -> str:
    try:
        import bcrypt
        pre = _prehash(password)
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pre, salt).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to hash password")

def verify_password(plain: str, hashed: str) -> bool:
    pre = _prehash(plain)
    try:
        import bcrypt
        return bcrypt.checkpw(pre, hashed.encode("utf-8"))
    except Exception:
        return False

async def create_email_verification_token(user_id: str) -> str:
    """
    Creates a single-use email verification token (24h expiry)
    and stores its hash in DB.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    tokens = get_collection("email_verification_tokens")

    await tokens.insert_one({
        "_id": str(uuid4()),
        "user_id": user_id,
        "token_hash": token_hash,
        "used": False,
        "expires_at": _now_utc() + timedelta(minutes=5),
        "created_at": _now_utc(),
    })

    return raw_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    company_name: str = Field(..., min_length=2)
    signup_source: str = "demo"  # demo | invite
    

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2)
    company: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(min_length=8)

class Token(BaseModel):
    user: Dict[str, Any]
    access_token: str
    refresh_token: str
class RefreshRequest(BaseModel):
    refresh_token: str
class EmailContinueRequest(BaseModel):
    token: str
class ForgotPasswordRequest(BaseModel):
    email: EmailStr
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6)

class StripeVerifyRequest(BaseModel):
    session_id: str


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    users = get_collection("users")
    user_doc = await users.find_one({"_id": user_id})
    if not user_doc:
        raise credentials_exception

    return {"id": user_doc["_id"], "email": user_doc["email"]}


async def _connection_statuses(user_id: str) -> Dict[str, bool]:
    quickbooks_tokens = await quickbooks_token_service.get_tokens_by_user(user_id)
    xero_tokens = await xero_token_service.get_tokens_by_user(user_id)
    return {
        "quickbooks_connected": any(token.is_active for token in quickbooks_tokens),
        "xero_connected": any(token.is_active for token in xero_tokens),
    }


async def _build_user_payload(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    created_at = user_doc.get("created_at")
    user_info = {
        "id": user_doc["_id"],
        "email": user_doc["email"],
        "name": user_doc.get("full_name"),
        "role": user_doc.get("role"),
        "created_at": created_at.isoformat() if created_at else None,
    }
    user_info.update(await _connection_statuses(user_doc["_id"]))
    return user_info


@router.get("/me")
async def get_current_user_details(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user details.
    Requires a valid access token.
    """
    try:
        users = get_collection("users")
        user_doc = await users.find_one({"_id": current_user["id"]})
        
        if not user_doc:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "User not found"}
            )
        
        if not user_doc.get("is_verified", False):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"success": False, "error": "Email not verified. Please verify your email."}
            )
            
        if user_doc.get("is_paused", False):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"success": False, "error": "Your account has been paused. Only admin can unpause your account. Contact Admin."}
            )


        user_info = await _build_user_payload(user_doc)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": user_info
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

# -----------------------
# Routes
# -----------------------
@router.post("/register")
async def register(user: UserCreate, request: Request):
    try:
        body = await request.json()
        if not isinstance(body, dict):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Invalid request body"}
            )

        allowed = {"email", "password", "full_name", "company_name"}
        extra = set(body.keys()) - allowed
        if extra:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": f"Unexpected fields: {', '.join(sorted(extra))}"
                }
            )

        users = get_collection("users")
        existing = await users.find_one({"email": user.email})

        if existing and existing.get("is_verified"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": "Email already registered. Please log in."
                }
            )

        if existing and not existing.get("is_verified"):
            tokens = get_collection("email_verification_tokens")
            await tokens.update_many(
                {"user_id": existing["_id"], "used": False},
                {"$set": {"used": True}}
            )

            verification_token = await create_email_verification_token(existing["_id"])

            verify_url = f"https://lightsignal.app/auth/verification?token={verification_token}"

            send_email(
                to_email=existing["email"],
                subject="Verify your LightSignal account",
                html_content=f"""
                <h2>Verify your LightSignal account</h2>
                <p>Your previous verification link expired.</p>
                <p>Please verify your email to continue.</p>
                <a href="{verify_url}"
                   style="display:inline-block;padding:12px 18px;
                          background:#2563eb;color:#ffffff;
                          text-decoration:none;border-radius:6px;">
                   Verify Email
                </a>
                <p>This link will expire in 10 minutes.</p>
                """
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": "You are already registered but not verified. Verification email resent. Please check your inbox."
                }
            )

        user_id = str(uuid4())
        
        # Get the global beta mode setting
        settings_collection = get_collection("system_settings")
        beta_mode_setting = await settings_collection.find_one({"_id": "beta_mode"})
        is_beta_mode_enabled = beta_mode_setting.get("is_beta_mode_enabled", False) if beta_mode_setting else False
        
        to_insert = {
            "_id": user_id,
            "full_name": user.full_name,
            "email": user.email,
            "password_hash": hash_password(user.password),
            "company_name": user.company_name,
            "is_verified": False,
            "is_beta": is_beta_mode_enabled,
            "role": "Viewer",  # Default role for new users
            "signup_source": user.signup_source,
            "is_paused": False,  # New accounts are not paused
            "last_active": _now_utc(),
            "created_at": _now_utc(),
        }

        await users.insert_one(to_insert)

        verification_token = await create_email_verification_token(user_id)
        verify_url = f"https://lightsignal.app/auth/verification?token={verification_token}"
        send_email(
            to_email=user.email,
            subject="Verify your LightSignal account",
            html_content=f"""
            <h2>Welcome to LightSignal 👋</h2>
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

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "data": {
                    "id": user_id,
                    "email": user.email
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.post("/login")
async def login(credentials: UserLogin):
    try:
        users = get_collection("users")
        user_doc = await users.find_one({"email": credentials.email})

        if not user_doc:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "error": "Invalid email or password"}
            )

        if not verify_password(credentials.password, user_doc.get("password_hash", "")):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "error": "Invalid email or password"}
            )

        if not user_doc.get("is_verified", False):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"success": False, "error": "Email not verified. Please verify your email."}
            )

        if user_doc.get("is_paused", False):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"success": False, "error": "Your account has been paused. Only admin can unpause your account. Contact Admin."}
            )

        # Update last_active
        await users.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {"last_active": _now_utc()}}
        )

        # Log login event for session tracking
        login_logs = get_collection("login_logs")
        await login_logs.insert_one({
            "user_id": user_doc["_id"],
            "login_time": _now_utc()
        })

        # Check if user has existing business profile
        business_profiles = get_collection("business_profiles")
        profile = await business_profiles.find_one({"user_id": user_doc["_id"]})
        has_existing_data = bool(profile)

        # ✅ Role handling (default Viewer)
        role = user_doc.get("role") or "Viewer"

        token_data = {
            "sub": str(user_doc["_id"]),
            "email": user_doc["email"],
            "role": role
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        user_info = await _build_user_payload(user_doc)
        user_info["role"] = role

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "has_existing_data": has_existing_data,
                "data": {
                    "user": user_info,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": "Internal server error"}
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(req: RefreshRequest):
    try:
        payload = jwt.decode(req.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "error": "Invalid refresh token"}
            )
    except JWTError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "error": "Invalid or expired refresh token"}
        )

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "error": "Invalid refresh token payload"}
        )

    users = get_collection("users")
    user_doc = await users.find_one({"_id": user_id})
    if not user_doc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "error": "User not found"}
        )

    new_access = create_access_token({"sub": user_id, "email": email})
    new_refresh = create_refresh_token({"sub": user_id, "email": email})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": {
                "access_token": new_access,
                "refresh_token": new_refresh,
            }
        }
    )
async def create_email_continue_token(user_id: str) -> str:
    """
    Creates a short-lived (10 min), single-use token
    for auto-login after email verification.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    tokens = get_collection("email_login_tokens")

    await tokens.insert_one({
        "_id": str(uuid4()),
        "user_id": user_id,
        "token_hash": token_hash,
        "used": False,
        "expires_at": _now_utc() + timedelta(minutes=10),
        "created_at": _now_utc(),
    })

    return raw_token

@router.get("/verification")
async def verify_email(token: str):
    """
    Verifies user's email using a single-use token.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    tokens = get_collection("email_verification_tokens")

    record = await tokens.find_one({"token_hash": token_hash})

    if not record:
        # Check if this verification token belongs to a pending signup that has paid
        pending_signups = get_collection("pending_signups")
        pending = await pending_signups.find_one({"verification_token_hash": token_hash})
        if pending:
            try:
                import stripe
                email = pending["email"]
                
                # Check Stripe for active subscriptions
                customers = stripe.Customer.list(email=email, limit=1)
                if customers.data:
                    customer = customers.data[0]
                    subs = stripe.Subscription.list(customer=customer.id, limit=1)
                    if subs.data and subs.data[0].status in ["active", "trialing"]:
                        sub = subs.data[0]
                        subscription_id = sub.id
                        customer_id = customer.id
                        trial_end = getattr(sub, "trial_end", None)
                        trial_ends_at = datetime.fromtimestamp(trial_end, tz=timezone.utc) if trial_end else None
                        
                        card_details = StripeService.get_card_details(subscription_id, customer_id)
                        user_id = str(uuid4())
                        
                        # Process user creation synchronously
                        users = get_collection("users")
                        new_user = {
                            "_id": user_id,
                            "full_name": pending["full_name"],
                            "email": pending["email"],
                            "password_hash": pending["password_hash"],
                            "company_name": pending["company_name"],
                            "is_verified": True,
                            "is_beta": False,
                            "role": "Viewer",
                            "signup_source": "stripe",
                            "is_paused": False,
                            "last_active": _now_utc(),
                            "created_at": _now_utc(),
                            "stripe_customer_id": customer_id,
                            "stripe_subscription_id": subscription_id,
                            "trial_ends_at": trial_ends_at,
                            "trial_warning_sent": False,
                            "card_details": card_details
                        }
                        await users.insert_one(new_user)
                        
                        # Save the verification token in tokens collection as used
                        await tokens.insert_one({
                            "_id": str(uuid4()),
                            "user_id": user_id,
                            "token_hash": token_hash,
                            "used": True,
                            "expires_at": _now_utc() + timedelta(hours=24),
                            "created_at": _now_utc(),
                        })
                        
                        await pending_signups.delete_one({"_id": pending["_id"]})
                        
                        continue_token = await create_email_continue_token(user_id)
                        return JSONResponse(
                            status_code=status.HTTP_200_OK,
                            content={
                                "success": True,
                                "continue_token": continue_token
                            }
                        )
            except Exception as sync_err:
                print(f"Error during synchronous verification process: {sync_err}")
                
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": "Invalid or expired verification link"
            }
        )

    expires_at = record.get("expires_at")

    # ✅ Fix: make expires_at timezone-aware if it is naive
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if record.get("used") or expires_at < _now_utc():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": "Invalid or expired verification link"
            }
        )

    users = get_collection("users")

    # Mark user as verified
    await users.update_one(
        {"_id": record["user_id"]},
        {"$set": {"is_verified": True}}
    )

    # Mark token as used
    await tokens.update_one(
        {"_id": record["_id"]},
        {"$set": {"used": True}}
    )
    continue_token = await create_email_continue_token(record["user_id"])
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "continue_token": continue_token
        }
    )

async def create_password_reset_token(user_id: str) -> str:
    """
    Creates a single-use password reset token (30 min expiry)
    and stores its hash in DB.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    tokens = get_collection("password_reset_tokens")

    await tokens.insert_one({
        "_id": str(uuid4()),
        "user_id": user_id,
        "token_hash": token_hash,
        "used": False,
        "expires_at": _now_utc() + timedelta(minutes=30),
        "created_at": _now_utc(),
    })

    return raw_token


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """
    Sends a password reset link to the user's email if an account exists.
    Always returns a generic success message to avoid leaking whether the email is registered.
    """
    try:
        users = get_collection("users")
        user_doc = await users.find_one({"email": payload.email})

        if user_doc:
            tokens = get_collection("password_reset_tokens")
            # Invalidate any previous unused reset links for this user
            await tokens.update_many(
                {"user_id": user_doc["_id"], "used": False},
                {"$set": {"used": True}}
            )

            reset_token = await create_password_reset_token(user_doc["_id"])
            reset_url = f"https://lightsignal.app/auth/reset-password?token={reset_token}"

            send_email(
                to_email=user_doc["email"],
                subject="Reset your LightSignal password",
                html_content=f"""
                <h2>Reset your password</h2>
                <p>We received a request to reset your LightSignal password.</p>
                <a href="{reset_url}"
                   style="display:inline-block;padding:12px 18px;
                          background:#2563eb;color:#ffffff;
                          text-decoration:none;border-radius:6px;">
                   Reset Password
                </a>
                <p>This link will expire in 30 minutes and can only be used once.</p>
                <p>If you did not request this, you can safely ignore this email.</p>
                """
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "If an account exists with this email, a password reset link has been sent."
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": "Internal server error"}
        )


@router.get("/reset-password/verify")
async def verify_reset_password_token(token: str):
    """
    Checks whether a password reset link is still valid, without consuming it.
    Called by the frontend when the reset page opens, before showing the new-password form.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    tokens = get_collection("password_reset_tokens")

    record = await tokens.find_one({"token_hash": token_hash})

    if not record:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": "Invalid or expired reset link"}
        )

    expires_at = record.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if record.get("used") or expires_at < _now_utc():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": "Invalid or expired reset link"}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "message": "Reset link is valid"}
    )


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    """
    Verifies a password reset token and sets the new password.
    The token is single-use: it is marked used as part of a successful reset
    and can never be opened again afterwards.
    """
    try:
        token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
        tokens = get_collection("password_reset_tokens")

        record = await tokens.find_one({"token_hash": token_hash})

        if not record:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Invalid or expired reset link"}
            )

        expires_at = record.get("expires_at")
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if record.get("used") or expires_at < _now_utc():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Invalid or expired reset link"}
            )

        users = get_collection("users")
        user_doc = await users.find_one({"_id": record["user_id"]})
        if not user_doc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Invalid or expired reset link"}
            )

        # Atomically claim the token so a concurrent request can't reuse it
        claim = await tokens.update_one(
            {"_id": record["_id"], "used": False},
            {"$set": {"used": True}}
        )
        if claim.modified_count == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Invalid or expired reset link"}
            )

        await users.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {"password_hash": hash_password(payload.new_password)}}
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": "Password has been reset successfully."}
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": "Internal server error"}
        )


@router.post("/email-continue")
async def email_continue(payload: EmailContinueRequest):
    token = payload.token

    """
    One-click login after email verification.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    tokens = get_collection("email_login_tokens")

    record = await tokens.find_one({"token_hash": token_hash})

    if not record:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    expires_at = record.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if record.get("used") or expires_at < _now_utc():
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    users = get_collection("users")
    user = await users.find_one({"_id": record["user_id"]})

    if not user or not user.get("is_verified"):
        raise HTTPException(status_code=403, detail="Email not verified")

    # Mark token as used
    await tokens.update_one(
        {"_id": record["_id"]},
        {"$set": {"used": True}}
    )

    token_data = {"sub": user["_id"], "email": user["email"]}

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": {
                "access_token": create_access_token(token_data),
                "refresh_token": create_refresh_token(token_data),
                "user": await _build_user_payload(user),
            }
        }
    )

@api_router.post("/signup")
async def signup(payload: SignupRequest, request: Request, background_tasks: BackgroundTasks):
    try:
        users = get_collection("users")
        existing = await users.find_one({"email": payload.email})

        if existing:
            if existing.get("is_verified"):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "success": False,
                        "error": "Email already registered. Please log in."
                    }
                )
            else:
                tokens = get_collection("email_verification_tokens")
                await tokens.update_many(
                    {"user_id": existing["_id"], "used": False},
                    {"$set": {"used": True}}
                )

                verification_token = await create_email_verification_token(existing["_id"])
                verify_url = f"https://lightsignal.app/auth/verification?token={verification_token}"

                background_tasks.add_task(
                    send_email,
                    to_email=existing["email"],
                    subject="Confirm your email to get started",
                    html_content=f"""
                    <h2>Confirm your email to get started</h2>
                    <p>Please confirm your email so we can keep your account secure.</p>
                    <a href="{verify_url}"
                       style="display:inline-block;padding:12px 18px;
                              background:#2563eb;color:#ffffff;
                              text-decoration:none;border-radius:6px;">
                       Verify Email
                    </a>
                    <p>This link will expire in 10 minutes.</p>
                    """,
                    from_email="hello@lightsignal.app"
                )

                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "success": True,
                        "message": "You are already registered but not verified. Verification email resent. Please check your inbox."
                    }
                )

        verification_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(verification_token.encode()).hexdigest()

        pending_signups = get_collection("pending_signups")
        await pending_signups.update_one(
            {"email": payload.email},
            {
                "$set": {
                    "full_name": payload.name,
                    "company_name": payload.company,
                    "password_hash": hash_password(payload.password),
                    "verification_token": verification_token,
                    "verification_token_hash": token_hash,
                    "created_at": _now_utc()
                }
            },
            upsert=True
        )

        success_url = f"{settings.stripe_success_url}?token={verification_token}"
        checkout_url = StripeService.create_checkout_session(payload.email, success_url=success_url)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "checkout_url": checkout_url
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        if not sig_header:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Missing stripe-signature header"}
            )

        try:
            event = StripeService.construct_webhook_event(payload, sig_header)
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": f"Invalid signature: {str(e)}"}
            )

        event_type = getattr(event, "type", None)
        event_data = getattr(event, "data", None)
        data_object = getattr(event_data, "object", None) if event_data else None

        if not event_type or not data_object:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Invalid event structure"}
            )

        if event_type == "checkout.session.completed":
            metadata = getattr(data_object, "metadata", None) or {}
            customer_details = getattr(data_object, "customer_details", None) or {}
            
            email = None
            if isinstance(metadata, dict):
                email = metadata.get("email")
            if not email and isinstance(customer_details, dict):
                email = customer_details.get("email")
            if not email:
                email = getattr(data_object, "customer_email", None)

            if not email:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"success": False, "error": "No email found in event"}
                )

            users = get_collection("users")
            existing = await users.find_one({"email": email})

            if not existing:
                pending_signups = get_collection("pending_signups")
                pending = await pending_signups.find_one({"email": email})
                if not pending:
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={"success": False, "error": f"No pending signup found for {email}"}
                    )

                subscription_id = getattr(data_object, "subscription", None)
                customer_id = getattr(data_object, "customer", None)
                trial_ends_at = None

                if subscription_id:
                    try:
                        import stripe
                        sub = stripe.Subscription.retrieve(subscription_id)
                        trial_end = getattr(sub, "trial_end", None)
                        if trial_end:
                            trial_ends_at = datetime.fromtimestamp(trial_end, tz=timezone.utc)
                    except Exception as sub_err:
                        print(f"Error fetching subscription details: {sub_err}")

                # Retrieve credit card details securely from Stripe
                card_details = StripeService.get_card_details(subscription_id, customer_id)

                user_id = str(uuid4())
                to_insert = {
                    "_id": user_id,
                    "full_name": pending["full_name"],
                    "email": pending["email"],
                    "password_hash": pending["password_hash"],
                    "company_name": pending["company_name"],
                    "is_verified": False,
                    "is_beta": False,
                    "role": "Viewer",
                    "signup_source": "stripe",
                    "is_paused": False,
                    "last_active": _now_utc(),
                    "created_at": _now_utc(),
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "trial_ends_at": trial_ends_at,
                    "trial_warning_sent": False,
                    "card_details": card_details
                }

                await users.insert_one(to_insert)

                pending_token_hash = pending.get("verification_token_hash")
                raw_token = pending.get("verification_token")
                
                if pending_token_hash and raw_token:
                    tokens = get_collection("email_verification_tokens")
                    await tokens.insert_one({
                        "_id": str(uuid4()),
                        "user_id": user_id,
                        "token_hash": pending_token_hash,
                        "used": False,
                        "expires_at": _now_utc() + timedelta(hours=24),
                        "created_at": _now_utc(),
                    })
                    verification_token = raw_token
                else:
                    verification_token = await create_email_verification_token(user_id)

                verify_url = f"https://lightsignal.app/auth/verification?token={verification_token}"
                
                background_tasks.add_task(
                    send_email,
                    to_email=email,
                    subject="Confirm your email to get started",
                    html_content=f"""
                    <h2>Welcome to LightSignal 👋</h2>
                    <p>Please verify your email to activate your account.</p>
                    <a href="{verify_url}"
                       style="display:inline-block;padding:12px 18px;
                              background:#2563eb;color:#ffffff;
                              text-decoration:none;border-radius:6px;">
                       Verify Email
                    </a>
                    <p>This link will expire in 10 minutes.</p>
                    """,
                    from_email="hello@lightsignal.app"
                )

                await pending_signups.delete_one({"_id": pending["_id"]})

        elif event_type == "customer.subscription.deleted":
            subscription_id = getattr(data_object, "id", None)
            users = get_collection("users")
            user = await users.find_one({"stripe_subscription_id": subscription_id})
            if user:
                await users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"is_paused": True, "subscription_status": "canceled"}}
                )

        elif event_type == "customer.subscription.updated":
            status_val = getattr(data_object, "status", None)
            subscription_id = getattr(data_object, "id", None)
            customer_id = getattr(data_object, "customer", None)

            users = get_collection("users")
            user = await users.find_one({"stripe_subscription_id": subscription_id})
            if user:
                if status_val in ["canceled", "unpaid"]:
                    await users.update_one(
                        {"_id": user["_id"]},
                        {"$set": {"is_paused": True, "subscription_status": status_val}}
                    )
                else:
                    trial_end_ts = getattr(data_object, "trial_end", None)
                    trial_ends_at = datetime.fromtimestamp(trial_end_ts, tz=timezone.utc) if trial_end_ts else None
                    card_details = StripeService.get_card_details(subscription_id, customer_id)
                    await users.update_one(
                        {"_id": user["_id"]},
                        {
                            "$set": {
                                "trial_ends_at": trial_ends_at,
                                "subscription_status": status_val,
                                "card_details": card_details
                            }
                        }
                    )

        return JSONResponse(status_code=200, content={"success": True})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

@router.get("/subscription/status")
async def get_subscription_status(current_user: dict = Depends(get_current_user)):
    """
    Returns the current logged-in user's subscription status, trial details, and card details.
    """
    try:
        users = get_collection("users")
        user = await users.find_one({"_id": current_user["id"]})
        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "User not found"}
            )
        
        trial_ends_at = user.get("trial_ends_at")
        trial_days_left = 0
        if trial_ends_at:
            if trial_ends_at.tzinfo is None:
                trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)
            delta = trial_ends_at - _now_utc()
            trial_days_left = max(0, delta.days)

        sub_status = user.get("subscription_status") or ("active" if user.get("is_beta") else "trialing")
        is_active = not user.get("is_paused", False)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "is_active": is_active,
                    "stripe_subscription_status": sub_status,
                    "is_beta": user.get("is_beta", False),
                    "trial_ends_at": trial_ends_at.isoformat() if trial_ends_at else None,
                    "trial_days_left": trial_days_left,
                    "card_details": user.get("card_details", {})
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

@api_router.post("/stripe-session/verify")
async def verify_stripe_session(payload: StripeVerifyRequest):
    """
    Directly verifies a Stripe Checkout Session status on success redirect.
    If the webhook hasn't processed the account creation yet, this endpoint processes it
    synchronously to avoid race conditions. Returns JWT tokens for instant auto-login.
    """
    try:
        import stripe
        session_id = payload.session_id
        
        # Retrieve checkout session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        payment_status = getattr(session, "payment_status", None)
        
        if not session or payment_status not in ["paid", "no_payment_required"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Checkout session is not paid or completed."}
            )
            
        metadata = getattr(session, "metadata", None) or {}
        customer_details = getattr(session, "customer_details", None) or {}
        
        email = None
        if isinstance(metadata, dict):
            email = metadata.get("email")
        if not email and isinstance(customer_details, dict):
            email = customer_details.get("email")
        if not email:
            email = getattr(session, "customer_email", None)
            
        if not email:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "No email found associated with this Stripe session."}
            )
            
        users = get_collection("users")
        user = await users.find_one({"email": email})
        
        if not user:
            # Webhook has not run yet. Process account creation immediately to avoid latency for the user
            pending_signups = get_collection("pending_signups")
            pending = await pending_signups.find_one({"email": email})
            if not pending:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"success": False, "error": f"No account or pending signup found for {email}"}
                )
                
            subscription_id = getattr(session, "subscription", None)
            customer_id = getattr(session, "customer", None)
            trial_ends_at = None

            if subscription_id:
                try:
                    sub = stripe.Subscription.retrieve(subscription_id)
                    trial_end = getattr(sub, "trial_end", None)
                    if trial_end:
                        trial_ends_at = datetime.fromtimestamp(trial_end, tz=timezone.utc)
                except Exception as sub_err:
                    print(f"Error fetching subscription details in direct verify: {sub_err}")

            card_details = StripeService.get_card_details(subscription_id, customer_id)
            user_id = str(uuid4())
            user = {
                "_id": user_id,
                "full_name": pending["full_name"],
                "email": pending["email"],
                "password_hash": pending["password_hash"],
                "company_name": pending["company_name"],
                "is_verified": True,  # Auto-verify directly upon checkout redirect success
                "is_beta": False,
                "role": "Viewer",
                "signup_source": "stripe",
                "is_paused": False,
                "last_active": _now_utc(),
                "created_at": _now_utc(),
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "trial_ends_at": trial_ends_at,
                "trial_warning_sent": False,
                "card_details": card_details
            }
            await users.insert_one(user)
            await pending_signups.delete_one({"_id": pending["_id"]})
        else:
            # If the user exists (webhook already run), ensure they are marked verified
            if not user.get("is_verified"):
                await users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"is_verified": True}}
                )
                user["is_verified"] = True
                
        # Generate JWT tokens for instant auto-login
        token_data = {"sub": user["_id"], "email": user["email"]}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        user_info = await _build_user_payload(user)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Session verified. User activated.",
                "data": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": user_info
                }
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )
