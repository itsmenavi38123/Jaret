import base64
import logging
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

AUTH_BASE_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

API_BASE_URLS = {
    "production": "https://quickbooks.api.intuit.com",
    "prod": "https://quickbooks.api.intuit.com",
    "live": "https://quickbooks.api.intuit.com",
    "sandbox": "https://sandbox-quickbooks.api.intuit.com",
    "development": "https://sandbox-quickbooks.api.intuit.com",
}

DEFAULT_QBO_SCOPE = "com.intuit.quickbooks.accounting openid profile email"
HARD_CODED_REDIRECT_URI = "https://biz-advisor-74.preview.emergentagent.com/api/quickbooks-oauth/callback"

logger = logging.getLogger(__name__)


class QuickBooksUnauthorizedError(Exception):
    """Raised when QuickBooks returns 401/authorization errors."""


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _basic_auth_header() -> str:
    client_id = _required_env("QUICKBOOKS_CLIENT_ID")
    client_secret = _required_env("QUICKBOOKS_CLIENT_SECRET")
    credentials = f"{client_id}:{client_secret}"
    return base64.b64encode(credentials.encode()).decode()


def get_api_base_url() -> str:
    env = (os.getenv("QUICKBOOKS_ENVIRONMENT") or "production").strip().lower()
    return API_BASE_URLS.get(env, API_BASE_URLS["production"])


def get_authorization_url(state: Optional[str] = None, redirect_uri: Optional[str] = None, scope: Optional[str] = None) -> str:
    """
    Build the authorization URL used to start the OAuth2 flow.
    """
    client_id = _required_env("QUICKBOOKS_CLIENT_ID")
    chosen_scope = scope or DEFAULT_QBO_SCOPE
    callback_uri = redirect_uri or HARD_CODED_REDIRECT_URI
    encoded_redirect = urllib.parse.quote(callback_uri, safe="")
    encoded_scope = urllib.parse.quote(chosen_scope, safe=" ")
    encoded_state = urllib.parse.quote(state or "secureRandomState123", safe="")

    url = (
        f"{AUTH_BASE_URL}"
        f"?client_id={urllib.parse.quote(client_id, safe='')}"
        f"&redirect_uri={encoded_redirect}"
        f"&response_type=code"
        f"&scope={encoded_scope}"
        f"&state={encoded_state}"
    )
    logger.info("Generated QuickBooks auth URL with redirect %s", callback_uri)
    return url


async def exchange_code_for_tokens(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """
    Exchange an authorization code for access/refresh tokens.
    """
    headers = {
        "Authorization": f"Basic {_basic_auth_header()}",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or HARD_CODED_REDIRECT_URI,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TOKEN_URL, data=data, headers=headers)
    except Exception as exc:  # network or transport errors
        logger.exception("QuickBooks token exchange failed to reach Intuit")
        raise HTTPException(status_code=502, detail="Failed to reach QuickBooks token endpoint") from exc

    if response.status_code != httpx.codes.OK:
        logger.error("QuickBooks token exchange error: %s", response.text)
        raise HTTPException(status_code=response.status_code, detail=response.text)

    payload = response.json()
    logger.info("QuickBooks token exchange succeeded; expires_in=%s", payload.get("expires_in"))
    return payload


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh the QuickBooks access token using a refresh token.
    """
    headers = {
        "Authorization": f"Basic {_basic_auth_header()}",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TOKEN_URL, data=data, headers=headers)
    except Exception as exc:
        logger.exception("QuickBooks refresh failed to reach Intuit")
        raise HTTPException(status_code=502, detail="Failed to reach QuickBooks token endpoint") from exc

    if response.status_code != httpx.codes.OK:
        logger.error("QuickBooks refresh error: %s", response.text)
        raise HTTPException(status_code=response.status_code, detail=response.text)

    payload = response.json()
    logger.info(
        "QuickBooks token refreshed; expires_in=%s x_refresh_token_expires_in=%s",
        payload.get("expires_in"),
        payload.get("x_refresh_token_expires_in"),
    )
    return payload


def token_has_expired(created_at: datetime, expires_in_seconds: int, safety_buffer: int = 120) -> bool:
    """
    Determine whether a token has expired.
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    buffer_seconds = max(safety_buffer, 0)
    expiry = created_at + timedelta(seconds=expires_in_seconds - buffer_seconds)
    return datetime.now(timezone.utc) >= expiry


async def _perform_qbo_request(
    method: str,
    url: str,
    access_token: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_payload: Optional[Dict[str, Any]] = None,
) -> httpx.Response:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.request(method, url, params=params, json=json_payload, headers=headers)
    except Exception as exc:
        logger.exception("QuickBooks API request failed: %s %s", method, url)
        raise HTTPException(status_code=502, detail="Failed to reach QuickBooks API") from exc

    if response.status_code in {401, 403}:
        logger.warning("QuickBooks unauthorized response: %s", response.text)
        raise QuickBooksUnauthorizedError(response.text)

    if response.status_code >= 400:
        logger.error("QuickBooks API error (%s): %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response


async def fetch_report(access_token: str, realm_id: str, report: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fetch a QuickBooks report (e.g., ProfitAndLoss, BalanceSheet).
    """
    base = get_api_base_url()
    url = f"{base}/v3/company/{realm_id}/reports/{report}"
    merged_params = {"minorversion": "73"}
    if params:
        merged_params.update(params)

    response = await _perform_qbo_request("GET", url, access_token, params=merged_params)
    # print(response.json())
    return response.json()


async def get_company_info(access_token: str, realm_id: str) -> Dict[str, Any]:
    """
    Fetch the QuickBooks company info resource.
    """
    base = get_api_base_url()
    url = f"{base}/v3/company/{realm_id}/companyinfo/{realm_id}"
    response = await _perform_qbo_request("GET", url, access_token, params={"minorversion": "73"})
    return response.json()
