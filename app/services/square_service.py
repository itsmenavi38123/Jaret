import httpx
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.config import settings


async def exchange_code_for_token(code: str) -> dict:
    url = "https://connect.squareup.com/oauth2/token"

    payload = {
        "client_id": settings.square_app_id,
        "client_secret": settings.square_app_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.pos_oauth_callback_url,  # 🔥 REQUIRED
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)  # 🔥 JSON, not form-data
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Square request failed: {str(exc)}"
        )

    # 🔥 show real error (VERY IMPORTANT for debugging)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Square error: {resp.text}"
        )

    data = resp.json()

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = data.get("expires_at") or data.get("expires_in")

    expires_at = None
    if isinstance(expires_in, int):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }