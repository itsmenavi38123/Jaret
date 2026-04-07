from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from urllib.parse import urlencode
import hashlib
import hmac
import re
import requests
from app.config import settings
from app.db import get_collection
from app.models.pos_models import OauthState
from app.routes.auth.auth import get_current_user
from app.services import square_service, shopify_service, clover_service, lightspeed_service
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["integrations"])

ALLOWED_PROVIDERS = {"square", "shopify", "clover", "lightspeed", "toast"}


class ConnectPosRequest(BaseModel):
    provider: str
    shop: Optional[str] = None

    @field_validator("provider")
    def validate_provider(cls, v: str) -> str:
        if v not in ALLOWED_PROVIDERS:
            raise ValueError("Invalid provider")
        return v

    @field_validator("shop")
    def validate_shop(cls, v, info):
        if info.data.get("provider") == "shopify" and not v:
            raise ValueError("Shop domain is required for Shopify")
        return v


def normalize_shopify_shop(shop: str) -> str:
    shop = shop.strip().lower()
    shop = shop.replace("https://", "").replace("http://", "")
    shop = shop.replace(".myshopify.com", "")
    shop = shop.split("/")[0]

    if not re.match(r"^[a-z0-9\-]+$", shop):
        raise HTTPException(status_code=400, detail="Invalid Shopify shop domain")

    return shop


def build_provider_config(provider: str, shop: str | None):
    if provider == "square":
        return {
            "client_id": settings.square_app_id,
            "base": "https://connect.squareup.com/oauth2/authorize",
            "extra_params": {"response_type": "code"},
        }
    if provider == "shopify":
        if not shop:
            raise HTTPException(status_code=400, detail="Shop domain is required for Shopify")

        shop = normalize_shopify_shop(shop)

        return {
            "client_id": settings.shopify_client_id,
            "base": f"https://{shop}.myshopify.com/admin/oauth/authorize",
            "extra_params": {
                "scope": settings.shopify_scopes,
                "grant_options[]": "per-user",
                "host": f"{shop}.myshopify.com",
            },
        }
    if provider == "clover":
        return {
            "client_id": settings.clover_app_id,
            "base": "https://sandbox.dev.clover.com/oauth/authorize",
            "extra_params": {"response_type": "code"},
        }
    
    if provider == "lightspeed":
        return {
            "client_id": settings.lightspeed_client_id,
            "base": "https://secure.vendhq.com/connect",
            "extra_params": {"response_type": "code"},
        }

    raise HTTPException(status_code=400, detail="Unsupported provider")


def build_shopify_hmac_message(query_params: dict[str, str]) -> str:
    pairs = []
    for key in sorted(query_params):
        if key in {"hmac", "signature"}:
            continue
        value = str(query_params[key]).replace("%", "%25").replace("&", "%26")
        pairs.append(f"{key}={value}")
    return "&".join(pairs)


def validate_shopify_callback(query_params: dict[str, str]) -> None:
    if not settings.shopify_client_secret:
        raise HTTPException(status_code=500, detail="Shopify client secret is not configured")
    provided_hmac = query_params.get("hmac")
    if not provided_hmac:
        raise HTTPException(status_code=400, detail="Missing Shopify HMAC")

    message = build_shopify_hmac_message(query_params)
    digest = hmac.new(
        settings.shopify_client_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(digest, provided_hmac):
        raise HTTPException(status_code=400, detail="Invalid Shopify callback signature")


@router.post("/integrations/connect")
async def connect_pos(
    body: ConnectPosRequest,
    current_user: dict = Depends(get_current_user),
):
    provider = body.provider
    user_id = current_user["id"]
    normalized_shop = normalize_shopify_shop(body.shop) if provider == "shopify" and body.shop else None

    state_val = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    oauth_obj = OauthState(
        state=state_val,
        user_id=user_id,
        provider=provider,
        expires_at=expires_at,
        shop=normalized_shop,
    )

    col = get_collection("oauth_states")
    await col.insert_one(oauth_obj.model_dump())

    config = build_provider_config(provider, normalized_shop)

    params = {
        "client_id": config["client_id"],
        "redirect_uri": settings.pos_oauth_callback_url,
        "state": state_val,
        **config["extra_params"],
    }

    redirect_url = f"{config['base']}?{urlencode(params)}"

    return {
        "success": True,
        "redirect_url": redirect_url,
    }

@router.get("/integrations/oauth/callback")
async def oauth_callback(
    request: Request,
    code: str,
    state: str,
    shop: Optional[str] = None,
):
    now = datetime.now(timezone.utc)
    states_col = get_collection("oauth_states")

    state_doc = await states_col.find_one({"state": state})
    if not state_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing state parameter"
        )

    # ✅ FIXED TIMEZONE ISSUE
    expires_at = state_doc.get("expires_at")
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            await states_col.delete_one({"state": state})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State has expired"
            )

    provider = state_doc.get("provider")
    user_id = state_doc.get("user_id")
    saved_shop = state_doc.get("shop")

    tokens: dict
    if provider == "square":
        tokens = await square_service.exchange_code_for_token(code)

    elif provider == "shopify":
        if not shop or not saved_shop:
            raise HTTPException(status_code=400, detail="Missing Shopify shop domain")

        normalized_shop = normalize_shopify_shop(shop)
        if normalized_shop != saved_shop:
            raise HTTPException(status_code=400, detail="Shopify shop does not match request state")

        validate_shopify_callback(dict(request.query_params))
        tokens = await shopify_service.exchange_code_for_token(code, normalized_shop)

        def create_shopify_webhook(shop, access_token):
            url = f"https://{shop}/admin/api/2023-10/webhooks.json"

            payload = {
                "webhook": {
                    "topic": "app/uninstalled",
                    "address": "https://api.lightsignal.app/webhooks/shopify/app-uninstalled",
                    "format": "json"
                }
            }

            headers = {
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json"
            }

            requests.post(url, json=payload, headers=headers)
        create_shopify_webhook(f"{normalized_shop}.myshopify.com", tokens.get("access_token"))

    elif provider == "clover":
        tokens = await clover_service.exchange_code_for_token(code)

    elif provider == "lightspeed":
        tokens = await lightspeed_service.exchange_code_for_token(code)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported provider"
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_at = tokens.get("expires_at")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to obtain access token from provider"
        )

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

    return RedirectResponse(
        url=f"https://api.lightsignal.app?shop={normalized_shop}.myshopify.com",
        status_code=302
    )


@router.post("/webhooks/shopify/app-uninstalled")
async def app_uninstalled(request: Request):
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")

    import base64
    digest = hmac.new(
        settings.shopify_client_secret.encode(),
        body,
        hashlib.sha256
    ).digest()

    computed = base64.b64encode(digest).decode()

    if not hmac.compare_digest(computed, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

    return {"success": True}