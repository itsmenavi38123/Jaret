from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from jose import jwt

from app.config import JWT_ALGORITHM, JWT_SECRET
from app.models.xero.token import XeroTokenCreate
from app.routes.auth.auth import get_current_user
from app.services import xero_service
from app.services.xero_token_service import xero_token_service

router = APIRouter()


@router.get("/login")
async def login(
    current_user: dict = Depends(get_current_user),
    redirect_uri: Optional[str] = Query(None, description="Optional callback override"),
    scope: Optional[str] = Query(None, description="Optional OAuth scope override"),
):
    state_payload = {
        "user_id": current_user["id"],
        "exp": datetime.utcnow() + timedelta(minutes=10),
    }
    if redirect_uri:
        state_payload["redirect_uri"] = redirect_uri

    state = jwt.encode(state_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    auth_url = xero_service.get_authorization_url(state, redirect_uri=redirect_uri, scope=scope)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {"auth_url": auth_url},
        }),
    )


@router.get("/tokens")
async def list_tokens(current_user: dict = Depends(get_current_user)):
    tokens = await xero_token_service.get_tokens_by_user(current_user["id"])
    serialized = [
        {
            "id": token.id,
            "tenant_id": token.tenant_id,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "scope": token.scope,
            "created_at": token.created_at,
            "updated_at": token.updated_at,
            "is_active": token.is_active,
        }
        for token in tokens
    ]
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": {"tokens": serialized, "count": len(serialized)}}),
    )


@router.get("/tokens/{tenant_id}")
async def get_token(tenant_id: str, current_user: dict = Depends(get_current_user)):
    token = await xero_token_service.get_token_by_user_and_tenant(current_user["id"], tenant_id)
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active token for tenant")
    payload = {
        "id": token.id,
        "tenant_id": token.tenant_id,
        "token_type": token.token_type,
        "expires_in": token.expires_in,
        "scope": token.scope,
        "created_at": token.created_at,
        "updated_at": token.updated_at,
        "is_active": token.is_active,
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"success": True, "data": payload}))


@router.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    state_token = request.query_params.get("state")

    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code")
    if not state_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state parameter")

    try:
        state_data = jwt.decode(state_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = state_data["user_id"]
        redirect_uri = state_data.get("redirect_uri")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter") from exc

    tokens = await xero_service.exchange_code_for_tokens(code, redirect_uri=redirect_uri)
    connections = await xero_service.get_connections(tokens["access_token"])
    if not connections:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No Xero connections found")

    tenant = connections[0]
    tenant_id = tenant.get("tenantId")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to determine tenant ID")

    token_record = XeroTokenCreate(
        user_id=user_id,
        tenant_id=tenant_id,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        scope=tokens.get("scope"),
        token_type=tokens.get("token_type", "Bearer"),
        expires_in=tokens.get("expires_in", 0),
    )
    stored_token = await xero_token_service.create_token(token_record)

    response_payload = {
        "success": True,
        "data": {
            "message": "Xero tokens stored successfully",
            "tenant_id": tenant_id,
            "token_id": stored_token.id,
            "expires_in": stored_token.expires_in,
            "token_type": stored_token.token_type,
        },
    }
    if redirect_uri:
        response_payload["data"]["redirect_uri"] = redirect_uri

    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(response_payload))
