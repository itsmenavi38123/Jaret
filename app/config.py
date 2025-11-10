from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from jose import jwt

class Settings(BaseSettings):
    app_name: str = "FastAPI Backend"
    app_version: str = "1.0.0"
    debug: bool = True

    mongo_uri: str
    mongo_db_name: str

    # QuickBooks
    quickbooks_client_id: str
    quickbooks_client_secret: str
    quickbooks_redirect_uri: str
    quickbooks_environment: str

    # Xero
    xero_client_id: Optional[str] = None
    xero_client_secret: Optional[str] = None
    xero_redirect_uri: Optional[str] = None

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
# -----------------------
# JWT configuration
# -----------------------
JWT_SECRET = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes  # minutes

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET_KEY must be set in environment")

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = _now_utc()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"iat": now, "exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = _now_utc()
    expire = now + (expires_delta or timedelta(days=7))
    to_encode.update({"iat": now, "exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)




