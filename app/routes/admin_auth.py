# backend/app/routes/admin_auth.py
"""
Dedicated platform-admin authentication: separate from the customer /auth/*
flow, gated on a real `is_admin` flag (never settable via any API), and
enforced with mandatory TOTP 2FA plus short, server-side-revocable sessions.
"""
from datetime import timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field

from app.config import JWT_ALGORITHM, JWT_SECRET, _now_utc
from app.db import get_collection
from app.routes.auth.auth import verify_password

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])

ADMIN_SETUP_TOKEN_EXPIRE_MINUTES = 10
ADMIN_TEMP_TOKEN_EXPIRE_MINUTES = 10
ADMIN_SESSION_EXPIRE_HOURS = 6

GENERIC_LOGIN_ERROR = "Invalid credentials"

_admin_bearer_scheme = HTTPBearer(auto_error=True)


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminSetupRequest(BaseModel):
    setup_token: str


class AdminSetupVerifyRequest(BaseModel):
    setup_token: str
    code: str = Field(..., min_length=6, max_length=6)


class AdminVerifyRequest(BaseModel):
    temp_token: str
    code: str = Field(..., min_length=6, max_length=6)


def _encode_short_token(user_id: str, token_type: str, expires_minutes: int) -> str:
    now = _now_utc()
    payload = {
        "sub": user_id,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str, expected_type: str) -> str:
    invalid_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise invalid_token_exception

    if payload.get("type") != expected_type:
        raise invalid_token_exception

    user_id = payload.get("sub")
    if not user_id:
        raise invalid_token_exception

    return user_id


async def _load_admin_user(user_id: str) -> Dict[str, Any]:
    """Re-checks is_admin on every step, in case it was revoked mid-flow."""
    users = get_collection("users")
    user_doc = await users.find_one({"_id": user_id})
    if not user_doc or not user_doc.get("is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user_doc


async def _create_admin_session(user_id: str) -> Dict[str, Any]:
    session_id = str(uuid4())
    now = _now_utc()
    expires_at = now + timedelta(hours=ADMIN_SESSION_EXPIRE_HOURS)

    sessions = get_collection("admin_sessions")
    await sessions.insert_one(
        {
            "_id": session_id,
            "user_id": user_id,
            "created_at": now,
            "expires_at": expires_at,
            "revoked": False,
        }
    )

    token = jwt.encode(
        {
            "sub": user_id,
            "jti": session_id,
            "type": "admin_session",
            "iat": now,
            "exp": expires_at,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"token": token, "expires_at": expires_at}


async def require_admin_session(
    creds: HTTPAuthorizationCredentials = Depends(_admin_bearer_scheme),
) -> Dict[str, Any]:
    """
    Validates a short-lived, DB-backed admin session token. Every /admin/*
    route depends on this (via require_admin_role in app.routes.admin) so
    admin access is enforced server-side, not by a client-trusted role string.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin session",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "admin_session":
        raise credentials_exception

    session_id = payload.get("jti")
    user_id = payload.get("sub")
    if not session_id or not user_id:
        raise credentials_exception

    sessions = get_collection("admin_sessions")
    session_doc = await sessions.find_one({"_id": session_id, "user_id": user_id})
    if not session_doc or session_doc.get("revoked", False):
        raise credentials_exception

    expires_at = session_doc.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not expires_at or expires_at < _now_utc():
        raise credentials_exception

    users = get_collection("users")
    user_doc = await users.find_one({"_id": user_id})
    if not user_doc or not user_doc.get("is_admin", False):
        raise credentials_exception

    return {"id": user_doc["_id"], "email": user_doc["email"], "session_id": session_id}


@router.post("/login")
async def admin_login(payload: AdminLoginRequest):
    """
    Password check step. Never reveals whether the account exists or is an
    admin account - wrong password, unknown email, and non-admin accounts
    all produce the same generic rejection.
    """
    users = get_collection("users")
    user_doc = await users.find_one({"email": payload.email})

    if (
        not user_doc
        or not verify_password(payload.password, user_doc.get("password_hash", ""))
        or not user_doc.get("is_admin", False)
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"success": False, "error": GENERIC_LOGIN_ERROR},
        )

    user_id = user_doc["_id"]

    if not user_doc.get("totp_enrolled", False):
        setup_token = _encode_short_token(user_id, "admin_2fa_setup", ADMIN_SETUP_TOKEN_EXPIRE_MINUTES)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "data": {"status": "needs_2fa_setup", "setup_token": setup_token}},
        )

    temp_token = _encode_short_token(user_id, "admin_2fa_temp", ADMIN_TEMP_TOKEN_EXPIRE_MINUTES)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": {"status": "needs_2fa_code", "temp_token": temp_token}},
    )


@router.post("/2fa/setup")
async def admin_2fa_setup(payload: AdminSetupRequest):
    """Generates a fresh TOTP secret. Not persisted as active until /2fa/setup/verify confirms it."""
    user_id = _decode_token(payload.setup_token, "admin_2fa_setup")
    user_doc = await _load_admin_user(user_id)

    if user_doc.get("totp_enrolled", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is already enrolled for this account")

    secret = pyotp.random_base32()
    users = get_collection("users")
    await users.update_one({"_id": user_id}, {"$set": {"totp_pending_secret": secret}})

    otpauth_url = pyotp.TOTP(secret).provisioning_uri(name=user_doc["email"], issuer_name="LightSignal Admin")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": {"secret": secret, "otpauth_url": otpauth_url}},
    )


@router.post("/2fa/setup/verify")
async def admin_2fa_setup_verify(payload: AdminSetupVerifyRequest):
    """Confirms the first code and, on success, both enrolls TOTP and issues the admin session."""
    user_id = _decode_token(payload.setup_token, "admin_2fa_setup")
    user_doc = await _load_admin_user(user_id)

    if user_doc.get("totp_enrolled", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is already enrolled for this account")

    pending_secret = user_doc.get("totp_pending_secret")
    if not pending_secret or not pyotp.TOTP(pending_secret).verify(payload.code, valid_window=1):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": "Invalid verification code"},
        )

    users = get_collection("users")
    await users.update_one(
        {"_id": user_id},
        {
            "$set": {"totp_secret": pending_secret, "totp_enrolled": True},
            "$unset": {"totp_pending_secret": ""},
        },
    )

    session = await _create_admin_session(user_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": {
                "status": "success",
                "access_token": session["token"],
                "expires_at": session["expires_at"].isoformat(),
            },
        },
    )


@router.post("/2fa/verify")
async def admin_2fa_verify(payload: AdminVerifyRequest):
    """For accounts with 2FA already enrolled: verifies the code and issues the admin session."""
    user_id = _decode_token(payload.temp_token, "admin_2fa_temp")
    user_doc = await _load_admin_user(user_id)

    secret = user_doc.get("totp_secret")
    if (
        not user_doc.get("totp_enrolled", False)
        or not secret
        or not pyotp.TOTP(secret).verify(payload.code, valid_window=1)
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": "Invalid verification code"},
        )

    session = await _create_admin_session(user_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": {
                "status": "success",
                "access_token": session["token"],
                "expires_at": session["expires_at"].isoformat(),
            },
        },
    )


@router.post("/logout")
async def admin_logout(current_admin: Dict[str, Any] = Depends(require_admin_session)):
    """Invalidates the admin session server-side - the token stops working immediately, everywhere."""
    sessions = get_collection("admin_sessions")
    await sessions.update_one(
        {"_id": current_admin["session_id"]},
        {"$set": {"revoked": True}},
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "message": "Logged out"})
