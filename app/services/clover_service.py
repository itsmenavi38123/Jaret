import httpx
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.config import settings


async def exchange_code_for_token(code: str) -> dict:
    url = "https://sandbox.dev.clover.com/oauth/token"
    data = {
        "client_id": settings.clover_app_id,
        "client_secret": settings.clover_app_secret,
        "code": code,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, data=data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to obtain access token from provider") from exc

    if resp.status_code != httpx.codes.OK:
        raise HTTPException(status_code=502, detail="Failed to obtain access token from provider")

    payload = resp.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    return {"access_token": access_token, "refresh_token": refresh_token, "expires_at": expires_at}