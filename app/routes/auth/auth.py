import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from app.config import JWT_SECRET, JWT_ALGORITHM, create_access_token, create_refresh_token, _now_utc
import hashlib

from app.db import get_collection
from app.services.quickbooks_token_service import quickbooks_token_service
from app.services.xero_token_service import xero_token_service

import secrets
from app.services.email_service import send_email
from datetime import timezone

router = APIRouter(tags=["auth"])

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _prehash(password: str) -> bytes:
    """
    Pre-hash arbitrary-length password with SHA-256 and return raw bytes.
    This ensures bcrypt always receives a fixed-length input (32 bytes).
    """
    return hashlib.sha256(password.encode("utf-8")).digest()

def hash_password(password: str) -> str:
    try:
        pre = _prehash(password)
        return pwd_ctx.hash(pre)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to hash password")

def verify_password(plain: str, hashed: str) -> bool:
    pre = _prehash(plain)
    try:
        return pwd_ctx.verify(pre, hashed)
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

class Token(BaseModel):
    user: Dict[str, Any]
    access_token: str
    refresh_token: str
class RefreshRequest(BaseModel):
    refresh_token: str
class EmailContinueRequest(BaseModel):
    token: str


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
        to_insert = {
            "_id": user_id,
            "full_name": user.full_name,
            "email": user.email,
            "password_hash": hash_password(user.password),
            "company_name": user.company_name,
            "is_verified": False,
            "is_beta": False, 
            "role": "Client",  # Default role for new users
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
