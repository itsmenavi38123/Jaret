import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from app.config import JWT_SECRET, JWT_ALGORITHM, create_access_token, create_refresh_token, _now_utc
import hashlib

from app.db import get_collection
from fastapi import Request

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
        # only accept access tokens here
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

# -----------------------
# Routes
# -----------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body")

    allowed = {"email", "password"}
    extra = set(body.keys()) - allowed
    if extra:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unexpected fields: {', '.join(sorted(extra))}. Only allowed fields: email, password"
        )

    users = get_collection("users")
    existing = await users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user_id = str(uuid4())
    to_insert = {
        "_id": user_id,
        "email": user.email,
        "password_hash": hash_password(user.password),
        "created_at": _now_utc(),
    }

    await users.insert_one(to_insert)
    return {"id": user_id, "email": user.email}

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    users = get_collection("users")
    user_doc = await users.find_one({"email": credentials.email})
    if not user_doc or not verify_password(credentials.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token_data = {"sub": user_doc["_id"], "email": user_doc["email"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    user_info = {
        "id": user_doc["_id"],
        "email": user_doc["email"],
        "created_at": user_doc.get("created_at"),
    }

    return Token(
        user=user_info,
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(req: RefreshRequest):
    try:
        payload = jwt.decode(req.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")

    # Optional: verify user still exists / is not disabled
    users = get_collection("users")
    user_doc = await users.find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access = create_access_token({"sub": user_id, "email": email})
    new_refresh = create_refresh_token({"sub": user_id, "email": email})
    return Token(access_token=new_access, refresh_token=new_refresh)