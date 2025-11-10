from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Optional, List
from app.routes.auth.auth import get_current_user
from app.services.xero_accounts_service import xero_accounts_service
from app.models.xero.accounts import (
    XeroAccountCreate, XeroBankAccountCreate, XeroAccountUpdate, 
    XeroBankAccountUpdate, XeroAccountArchiveRequest, ACCOUNT_TYPES, BANK_ACCOUNT_TYPES, TAX_TYPES
)

router = APIRouter()

@router.get("/account-types")
async def get_account_types(current_user: dict = Depends(get_current_user)):
    """
    Get available account types for Xero accounts
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {
                "account_types": ACCOUNT_TYPES,
                "bank_account_types": BANK_ACCOUNT_TYPES,
                "tax_types": TAX_TYPES
            }
        })
    )

@router.post("/accounts")
async def create_account(
    account_data: XeroAccountCreate,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new account in Xero
    
    Required fields:
    - Name: Name of account (max length = 150)
    - Type: Account type (see /account-types for available types)
    
    Optional fields:
    - Code: Customer defined alpha numeric account code (max length = 10)
    - Status: ACTIVE or ARCHIVED (default: ACTIVE)
    - Description: Description of the Account (max length = 4000)
    - TaxType: Tax type (see /account-types for available types)
    - EnablePaymentsToAccount: Boolean (default: false)
    - ShowInExpenseClaims: Boolean (default: false)
    - AddToWatchlist: Boolean (default: false)
    """
    try:
        account = await xero_accounts_service.create_account(account_data, access_token, tenant_id)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder({
                "success": True,
                "data": {
                    "account": account,
                    "message": "Account created successfully"
                }
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )

@router.post("/bank-accounts")
async def create_bank_account(
    account_data: XeroBankAccountCreate,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new bank account in Xero
    
    Required fields:
    - Name: Name of account (max length = 150)
    - Type: Must be "BANK"
    - BankAccountNumber: Bank account number
    
    Optional fields:
    - Code: Customer defined alpha numeric account code (max length = 10)
    - BankAccountType: Type of bank account (see /account-types for available types)
    - CurrencyCode: Currency code for the account
    - Status: ACTIVE or ARCHIVED (default: ACTIVE)
    - Description: Description of the Account (max length = 4000)
    - EnablePaymentsToAccount: Boolean (default: false)
    - ShowInExpenseClaims: Boolean (default: false)
    """
    try:
        account = await xero_accounts_service.create_bank_account(account_data, access_token, tenant_id)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder({
                "success": True,
                "data": {
                    "account": account,
                    "message": "Bank account created successfully"
                }
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bank account: {str(e)}"
        )

@router.get("/accounts")
async def get_accounts(
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    where: Optional[str] = Query(None, description="Filter clause (e.g., 'Type==\"SALES\"')"),
    order: Optional[str] = Query(None, description="Order clause (e.g., 'Name ASC')"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all accounts from Xero
    
    Optional query parameters:
    - where: Filter clause (e.g., 'Type=="SALES"', 'Status=="ACTIVE"')
    - order: Order clause (e.g., 'Name ASC', 'Code DESC')
    """
    try:
        accounts = await xero_accounts_service.get_accounts(access_token, tenant_id, where, order)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": {
                    "accounts": accounts,
                    "count": len(accounts)
                }
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve accounts: {str(e)}"
        )

@router.get("/accounts/{account_id}")
async def get_account(
    account_id: str,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific account by ID
    """
    try:
        account = await xero_accounts_service.get_account(account_id, access_token, tenant_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": {
                    "account": account
                }
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve account: {str(e)}"
        )

@router.put("/accounts/{account_id}")
async def update_account(
    account_id: str,
    account_data: XeroAccountUpdate,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing account in Xero
    
    Note: You cannot update the status to archived when also updating other values.
    Use the archive endpoint for archiving accounts.
    
    Optional fields:
    - Code: Customer defined alpha numeric account code (max length = 10)
    - Name: Name of account (max length = 150)
    - Type: Account type
    - Description: Description of the Account (max length = 4000)
    - TaxType: Tax type
    - EnablePaymentsToAccount: Boolean
    - ShowInExpenseClaims: Boolean
    """
    try:
        # Ensure AccountID is set
        account_data.AccountID = account_id
        account = await xero_accounts_service.update_account(account_id, account_data, access_token, tenant_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": {
                    "account": account,
                    "message": "Account updated successfully"
                }
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account: {str(e)}"
        )

@router.put("/bank-accounts/{account_id}")
async def update_bank_account(
    account_id: str,
    account_data: XeroBankAccountUpdate,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing bank account in Xero
    
    Note: You cannot update the Bank Account Type.
    
    Optional fields:
    - Code: Customer defined alpha numeric account code (max length = 10)
    - Name: Name of account (max length = 150)
    - BankAccountNumber: Bank account number
    - CurrencyCode: Currency code for the account
    - Status: ACTIVE or ARCHIVED
    - Description: Description of the Account (max length = 4000)
    """
    try:
        # Ensure AccountID is set
        account_data.AccountID = account_id
        account = await xero_accounts_service.update_bank_account(account_id, account_data, access_token, tenant_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": {
                    "account": account,
                    "message": "Bank account updated successfully"
                }
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update bank account: {str(e)}"
        )

@router.post("/accounts/{account_id}/archive")
async def archive_account(
    account_id: str,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Archive an account in Xero
    
    Sets the account status to ARCHIVED.
    """
    try:
        result = await xero_accounts_service.archive_account(account_id, access_token, tenant_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": result
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive account: {str(e)}"
        )

@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an account from Xero
    
    Note: Only non-system accounts and accounts not used on transactions can be deleted.
    If an account cannot be deleted, you can archive it instead.
    """
    try:
        result = await xero_accounts_service.delete_account(account_id, access_token, tenant_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "success": True,
                "data": result
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )

@router.post("/accounts/{account_id}/attachments")
async def upload_attachment(
    account_id: str,
    file: UploadFile = File(..., description="File to upload"),
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload an attachment to a Xero account
    
    You can upload up to 10 attachments (each up to 25MB in size) per account.
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file size (25MB limit)
        if len(file_content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 25MB limit"
            )
        
        result = await xero_accounts_service.upload_attachment(
            account_id, 
            file.filename, 
            file_content, 
            file.content_type or "application/octet-stream",
            access_token, 
            tenant_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder({
                "success": True,
                "data": {
                    "message": "Attachment uploaded successfully",
                    "attachment": result
                }
            })
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload attachment: {str(e)}"
        )

@router.get("/accounts/{account_id}/attachments")
async def get_attachments(
    account_id: str,
    access_token: str = Query(..., description="Xero access token"),
    tenant_id: str = Query(..., description="Xero tenant/organization ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all attachments for a Xero account
    """
    # This would typically call a method to get attachments
    # For now, returning a placeholder response
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {
                "message": "Get attachments functionality to be implemented",
                "account_id": account_id
            }
        })
    )