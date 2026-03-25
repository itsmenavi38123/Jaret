from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.db import get_collection
from app.models.pos_models import OauthState
from app.routes.auth.auth import get_current_user
from app.services import square_service, shopify_service, clover_service, lightspeed_service

router = APIRouter(tags=["integrations"])


class ConnectPosRequest(BaseModel):
    provider: str
    shop: Optional[str] = None

    @field_validator("provider")
    def validate_provider(cls, v: str) -> str:
        allowed = {"square", "shopify", "clover", "lightspeed", "toast"}
        if v not in allowed:
            raise ValueError("provider must be one of: square, shopify, clover, lightspeed, toast")
        return v


@router.get("/integrations/connect")
async def connect_pos(  
    body: ConnectPosRequest,
    current_user: dict = Depends(get_current_user),
):

    user_id = current_user["id"]
    provider = body.provider

    state_val = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    oauth_obj = OauthState(
        state=state_val,
        user_id=user_id,
        provider=provider,
        expires_at=expires_at,
    )

    col = get_collection("oauth_states")
    await col.insert_one(oauth_obj.model_dump())

    if provider == "square":
        client_id = settings.square_app_id
        base = "https://connect.squareup.com/oauth2/authorize"

    elif provider == "shopify":
        client_id = settings.shopify_client_id
        shop = body.shop
        base = f"https://{shop}.myshopify.com/admin/oauth/authorize"

    elif provider == "clover":
        client_id = settings.clover_app_id
        base = "https://sandbox.dev.clover.com/oauth/authorize"

    elif provider == "lightspeed":
        client_id = settings.lightspeed_client_id
        base = "https://cloud.lightspeedapp.com/oauth/authorize.php"

    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    redirect_url = (
        f"{base}?client_id={client_id}"
        f"&redirect_uri={settings.pos_oauth_callback_url}"
        f"&response_type=code"
        f"&state={state_val}"
    )

    return {
        "success": True,
        "redirect_url": redirect_url
    }


@router.get("/integrations/oauth/callback")
async def oauth_callback(
    code: str,
    state: str,
):

    now = datetime.now(timezone.utc)
    states_col = get_collection("oauth_states")
    state_doc = await states_col.find_one({"state": state})
    if not state_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or missing state parameter")

    if state_doc.get("expires_at") and state_doc["expires_at"] < now:
        await states_col.delete_one({"state": state})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State has expired")

    provider = state_doc.get("provider")
    user_id = state_doc.get("user_id")

    # exchange code for tokens with the appropriate service
    tokens: dict
    if provider == "square":
        tokens = await square_service.exchange_code_for_token(code)
    elif provider == "shopify":
        tokens = await shopify_service.exchange_code_for_token(code)
    elif provider == "clover":
        tokens = await clover_service.exchange_code_for_token(code)
    elif provider == "lightspeed":
        tokens = await lightspeed_service.exchange_code_for_token(code)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_at = tokens.get("expires_at")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to obtain access token from provider")

    upsert_doc = {
        "user_id": user_id,
        "provider": provider,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    user_col = get_collection("user_pos_access")
    await user_col.update_one(
    {"user_id": user_id, "provider": provider},
    {
        "$set": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "updated_at": datetime.now(timezone.utc),
        },
        "$setOnInsert": {
            "created_at": datetime.now(timezone.utc),
            "user_id": user_id,
            "provider": provider,
        }
    },
    upsert=True,
    )    
    await states_col.delete_one({"state": state})

    return {"success": True, "provider": provider, "message": "POS connected successfully"}