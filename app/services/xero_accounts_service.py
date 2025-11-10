import httpx
import json
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from app.config import settings
from app.models.xero.accounts import (
    XeroAccountCreate, XeroBankAccountCreate, XeroAccountUpdate, 
    XeroBankAccountUpdate, XeroAccountResponse, XeroAccountArchiveRequest
)

XERO_API_BASE_URL = "https://api.xero.com/api.xro/2.0"

class XeroAccountsService:
    def __init__(self):
        self.base_url = XERO_API_BASE_URL
        
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get standard headers for Xero API requests"""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Xero-tenant-id": "{tenant_id}"  # This will be replaced with actual tenant ID
        }
    
    async def _make_request(self, method: str, endpoint: str, access_token: str, tenant_id: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Xero API"""
        headers = self._get_headers(access_token)
        headers["Xero-tenant-id"] = tenant_id
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 204:
                    return {"status": "success", "message": "Account deleted successfully"}
                else:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("Detail", error_detail)
                    except:
                        pass
                    
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Xero API error: {error_detail}"
                    )
                    
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Error connecting to Xero API: {str(e)}"
                )
    
    async def create_account(self, account_data: XeroAccountCreate, access_token: str, tenant_id: str) -> XeroAccountResponse:
        """
        Create a new account in Xero
        
        Args:
            account_data: Account creation data
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            
        Returns:
            Created account details
        """
        # Prepare the request data
        request_data = {
            "Accounts": [account_data.dict(exclude_none=True)]
        }
        
        response = await self._make_request("PUT", "/Accounts", access_token, tenant_id, request_data)
        
        # Xero returns the created account in the response
        if "Accounts" in response and len(response["Accounts"]) > 0:
            return XeroAccountResponse(**response["Accounts"][0])
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create account - no account returned"
            )
    
    async def create_bank_account(self, account_data: XeroBankAccountCreate, access_token: str, tenant_id: str) -> XeroAccountResponse:
        """
        Create a new bank account in Xero
        
        Args:
            account_data: Bank account creation data
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            
        Returns:
            Created bank account details
        """
        # Bank accounts are created the same way as regular accounts
        return await self.create_account(account_data, access_token, tenant_id)
    
    async def get_accounts(self, access_token: str, tenant_id: str, where: Optional[str] = None, order: Optional[str] = None) -> List[XeroAccountResponse]:
        """
        Get all accounts from Xero
        
        Args:
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            where: Optional filter clause
            order: Optional order clause
            
        Returns:
            List of accounts
        """
        params = {}
        if where:
            params["where"] = where
        if order:
            params["order"] = order
            
        # Build query string
        query_string = ""
        if params:
            query_string = "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        response = await self._make_request("GET", f"/Accounts{query_string}", access_token, tenant_id)
        
        if "Accounts" in response:
            return [XeroAccountResponse(**account) for account in response["Accounts"]]
        else:
            return []
    
    async def get_account(self, account_id: str, access_token: str, tenant_id: str) -> XeroAccountResponse:
        """
        Get a specific account by ID
        
        Args:
            account_id: Xero account ID
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            
        Returns:
            Account details
        """
        response = await self._make_request("GET", f"/Accounts/{account_id}", access_token, tenant_id)
        
        if "Accounts" in response and len(response["Accounts"]) > 0:
            return XeroAccountResponse(**response["Accounts"][0])
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID {account_id} not found"
            )
    
    async def update_account(self, account_id: str, account_data: XeroAccountUpdate, access_token: str, tenant_id: str) -> XeroAccountResponse:
        """
        Update an existing account in Xero
        
        Args:
            account_id: Xero account ID
            account_data: Account update data
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            
        Returns:
            Updated account details
        """
        # Prepare the request data
        update_data = account_data.dict(exclude_none=True)
        update_data["AccountID"] = account_id
        
        request_data = {
            "Accounts": [update_data]
        }
        
        response = await self._make_request("POST", f"/Accounts/{account_id}", access_token, tenant_id, request_data)
        
        if "Accounts" in response and len(response["Accounts"]) > 0:
            return XeroAccountResponse(**response["Accounts"][0])
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update account - no account returned"
            )
    
    async def update_bank_account(self, account_id: str, account_data: XeroBankAccountUpdate, access_token: str, tenant_id: str) -> XeroAccountResponse:
        """
        Update an existing bank account in Xero
        
        Args:
            account_id: Xero account ID
            account_data: Bank account update data
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            
        Returns:
            Updated bank account details
        """
        # Bank accounts are updated the same way as regular accounts
        return await self.update_account(account_id, account_data, access_token, tenant_id)
    
    async def archive_account(self, account_id: str, access_token: str, tenant_id: str) -> Dict[str, Any]:
        """
        Archive an account in Xero
        
        Args:
            account_id: Xero account ID
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            
        Returns:
            Success message
        """
        archive_data = {
            "Accounts": [{
                "AccountID": account_id,
                "Status": "ARCHIVED"
            }]
        }
        
        response = await self._make_request("POST", f"/Accounts/{account_id}", access_token, tenant_id, archive_data)
        
        if "Accounts" in response and len(response["Accounts"]) > 0:
            return {"status": "success", "message": "Account archived successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to archive account"
            )
    
    async def delete_account(self, account_id: str, access_token: str, tenant_id: str) -> Dict[str, Any]:
        """
        Delete an account from Xero (only if it's not used in transactions)
        
        Args:
            account_id: Xero account ID
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            
        Returns:
            Success message
        """
        response = await self._make_request("DELETE", f"/Accounts/{account_id}", access_token, tenant_id)
        
        return {"status": "success", "message": "Account deleted successfully"}
    
    async def upload_attachment(self, account_id: str, file_name: str, file_content: bytes, content_type: str, access_token: str, tenant_id: str) -> Dict[str, Any]:
        """
        Upload an attachment to a Xero account
        
        Args:
            account_id: Xero account ID
            file_name: Name of the file
            file_content: File content as bytes
            content_type: MIME type of the file
            access_token: Xero access token
            tenant_id: Xero tenant/organization ID
            
        Returns:
            Attachment details
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
            "Content-Length": str(len(file_content)),
            "Xero-tenant-id": tenant_id
        }
        
        url = f"{self.base_url}/Accounts/{account_id}/Attachments/{file_name}"
        
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, content=file_content)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 201:
                return {"status": "success", "message": "Attachment uploaded successfully"}
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("Detail", error_detail)
                except:
                    pass
                
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Xero API error: {error_detail}"
                )

# Create a singleton instance
xero_accounts_service = XeroAccountsService()