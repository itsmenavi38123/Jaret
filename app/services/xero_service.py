import base64
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from app.config import settings
from app.services.system_health_logs_service import system_health_logs_service
from app.models.system_health_logs import SystemHealthLogCreate

AUTH_BASE_URL = "https://login.xero.com/identity/connect/authorize"
TOKEN_URL = "https://identity.xero.com/connect/token"
CONNECTIONS_URL = "https://api.xero.com/connections"
DEFAULT_SCOPE = "offline_access openid profile email accounting.transactions accounting.settings accounting.contacts"


def _client_auth_header() -> str:
    credentials = f"{settings.xero_client_id}:{settings.xero_client_secret}".encode()
    return base64.b64encode(credentials).decode()


def get_authorization_url(state: str, redirect_uri: Optional[str] = None, scope: Optional[str] = None) -> str:
    callback = redirect_uri or settings.xero_redirect_uri
    requested_scope = scope or DEFAULT_SCOPE
    return (
        f"{AUTH_BASE_URL}?response_type=code"
        f"&client_id={settings.xero_client_id}"
        f"&redirect_uri={callback}"
        f"&scope={requested_scope}"
        f"&state={state}"
    )


async def exchange_code_for_tokens(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or settings.xero_redirect_uri,
    }
    headers = {
        "Authorization": f"Basic {_client_auth_header()}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(TOKEN_URL, data=payload, headers=headers)

    if response.status_code != httpx.codes.OK:
        # Log API error
        await system_health_logs_service.log_error(SystemHealthLogCreate(
            log_type="api_error",
            service="xero",
            endpoint="token_exchange",
            error_message=f"Xero token exchange failed: {response.text}",
            status_code=response.status_code
        ))
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {
        "Authorization": f"Basic {_client_auth_header()}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(TOKEN_URL, data=payload, headers=headers)

    if response.status_code != httpx.codes.OK:
        # Log API error
        await system_health_logs_service.log_error(SystemHealthLogCreate(
            log_type="api_error",
            service="xero",
            endpoint="token_refresh",
            error_message=f"Xero token refresh failed: {response.text}",
            status_code=response.status_code
        ))
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


async def get_connections(access_token: str) -> list[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(CONNECTIONS_URL, headers=headers)
    if response.status_code != httpx.codes.OK:
        # Log API error
        await system_health_logs_service.log_error(SystemHealthLogCreate(
            log_type="api_error",
            service="xero",
            endpoint="connections",
            error_message=f"Xero get connections failed: {response.text}",
            status_code=response.status_code
        ))
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
