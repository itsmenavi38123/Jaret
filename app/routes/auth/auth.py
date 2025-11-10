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



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    user: Dict[str, Any]
    access_token: str
    refresh_token: str
class RefreshRequest(BaseModel):
    refresh_token: str


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

        created_at = user_doc.get("created_at")
        user_info = {
            "id": user_doc["_id"],
            "email": user_doc["email"],
            "created_at": created_at.isoformat() if created_at else None,
        }

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
            return {
                "success": False,
                "error": "Invalid request body",
                "status_code": status.HTTP_400_BAD_REQUEST
            }

        allowed = {"email", "password"}
        extra = set(body.keys()) - allowed
        if extra:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": f"Unexpected fields: {', '.join(sorted(extra))}. Only allowed fields: email, password"
                }
            )

        users = get_collection("users")
        existing = await users.find_one({"email": user.email})
        if existing:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Email already registered"}
            )

        user_id = str(uuid4())
        to_insert = {
            "_id": user_id,
            "email": user.email,
            "password_hash": hash_password(user.password),
            "created_at": _now_utc(),
        }

        await users.insert_one(to_insert)

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

        if not user_doc or not verify_password(credentials.password, user_doc.get("password_hash", "")):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "error": "Invalid email or password"}
            )

        token_data = {"sub": user_doc["_id"], "email": user_doc["email"]}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        created_at = user_doc.get("created_at")
        user_info = {
            "id": user_doc["_id"],
            "email": user_doc["email"],
            "created_at": created_at.isoformat() if created_at else None,
        }

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
            content={"success": False, "error": str(e)}
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
