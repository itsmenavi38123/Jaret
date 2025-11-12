from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.models.xero.accounts import (
    ACCOUNT_TYPES,
    BANK_ACCOUNT_TYPES,
    TAX_TYPES,
    XeroAccountArchiveRequest,
    XeroAccountCreate,
    XeroAccountUpdate,
    XeroBankAccountCreate,
    XeroBankAccountUpdate,
)
from app.routes.auth.auth import get_current_user
from app.services.xero_accounts_service import xero_accounts_service

router = APIRouter()


@router.get("/account-types")
async def account_types(current_user: dict = Depends(get_current_user)):
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {
                "account_types": ACCOUNT_TYPES,
                "bank_account_types": BANK_ACCOUNT_TYPES,
                "tax_types": TAX_TYPES,
            },
        }),
    )


def _require_tokens(access_token: str, tenant_id: str) -> None:
    if not access_token or not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Xero credentials")


@router.post("/accounts")
async def create_account(
    account: XeroAccountCreate,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    payload = account.dict(exclude_none=True)
    created = await xero_accounts_service.create_account(payload, access_token, tenant_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder({"success": True, "data": {"account": created}}),
    )


@router.post("/bank-accounts")
async def create_bank_account(
    account: XeroBankAccountCreate,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    payload = account.dict(exclude_none=True)
    created = await xero_accounts_service.create_account(payload, access_token, tenant_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder({"success": True, "data": {"account": created}}),
    )


@router.get("/accounts")
async def list_accounts(
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    where: Optional[str] = Query(None, description="Xero 'where' filter"),
    order: Optional[str] = Query(None, description="Xero 'order' clause"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    accounts = await xero_accounts_service.get_accounts(access_token, tenant_id, where, order)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": {"accounts": accounts, "count": len(accounts)}}),
    )


@router.get("/accounts/{account_id}")
async def retrieve_account(
    account_id: str,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    account = await xero_accounts_service.get_account(account_id, access_token, tenant_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"success": True, "data": {"account": account}}))


@router.put("/accounts/{account_id}")
async def update_account(
    account_id: str,
    update: XeroAccountUpdate,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    payload = update.dict(exclude_none=True)
    payload["AccountID"] = account_id
    account = await xero_accounts_service.update_account(account_id, payload, access_token, tenant_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"success": True, "data": {"account": account}}))


@router.put("/bank-accounts/{account_id}")
async def update_bank_account(
    account_id: str,
    update: XeroBankAccountUpdate,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    payload = update.dict(exclude_none=True)
    payload["AccountID"] = account_id
    account = await xero_accounts_service.update_account(account_id, payload, access_token, tenant_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"success": True, "data": {"account": account}}))


@router.post("/accounts/{account_id}/archive")
async def archive_account(
    account_id: str,
    request: XeroAccountArchiveRequest,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    result = await xero_accounts_service.archive_account(account_id, access_token, tenant_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"success": True, "data": result}))


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    result = await xero_accounts_service.delete_account(account_id, access_token, tenant_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder({"success": True, "data": result}))


@router.post("/accounts/{account_id}/attachments")
async def upload_attachment(
    account_id: str,
    file: UploadFile = File(...),
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant ID"),
    current_user: dict = Depends(get_current_user),
):
    _require_tokens(access_token, tenant_id)
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 25MB limit")
    result = await xero_accounts_service.upload_attachment(
        account_id,
        file.filename,
        content,
        file.content_type or "application/octet-stream",
        access_token,
        tenant_id,
    )
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=jsonable_encoder({"success": True, "data": result}))
