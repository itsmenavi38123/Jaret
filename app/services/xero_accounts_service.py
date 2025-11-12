from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

XERO_API_BASE_URL = "https://api.xero.com/api.xro/2.0"


class XeroAccountsService:
    async def _request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        tenant_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{XERO_API_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Xero-tenant-id": tenant_id,
        }

        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.request(method, url, json=payload, headers=headers)

        if response.status_code in {200, 201}:
            return response.json()
        if response.status_code == 204:
            return {"status": "success"}

        detail = response.text
        try:
            detail = response.json()
        except Exception:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)

    async def create_account(self, account: Dict[str, Any], access_token: str, tenant_id: str) -> Dict[str, Any]:
        payload = {"Accounts": [account]}
        data = await self._request("PUT", "/Accounts", access_token, tenant_id, payload)
        return data.get("Accounts", [{}])[0]

    async def update_account(self, account_id: str, account: Dict[str, Any], access_token: str, tenant_id: str) -> Dict[str, Any]:
        payload = {"Accounts": [account]}
        data = await self._request("POST", f"/Accounts/{account_id}", access_token, tenant_id, payload)
        return data.get("Accounts", [{}])[0]

    async def get_accounts(
        self,
        access_token: str,
        tenant_id: str,
        where: Optional[str] = None,
        order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query: List[str] = []
        if where:
            query.append(f"where={where}")
        if order:
            query.append(f"order={order}")
        suffix = f"?{'&'.join(query)}" if query else ""
        data = await self._request("GET", f"/Accounts{suffix}", access_token, tenant_id)
        return data.get("Accounts", [])

    async def get_account(self, account_id: str, access_token: str, tenant_id: str) -> Dict[str, Any]:
        data = await self._request("GET", f"/Accounts/{account_id}", access_token, tenant_id)
        accounts = data.get("Accounts", [])
        if not accounts:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        return accounts[0]

    async def archive_account(self, account_id: str, access_token: str, tenant_id: str) -> Dict[str, Any]:
        payload = {"Accounts": [{"AccountID": account_id, "Status": "ARCHIVED"}]}
        await self._request("POST", f"/Accounts/{account_id}", access_token, tenant_id, payload)
        return {"status": "success", "message": "Account archived"}

    async def delete_account(self, account_id: str, access_token: str, tenant_id: str) -> Dict[str, Any]:
        await self._request("DELETE", f"/Accounts/{account_id}", access_token, tenant_id)
        return {"status": "success", "message": "Account deleted"}

    async def upload_attachment(
        self,
        account_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
        access_token: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
            "Content-Length": str(len(file_content)),
            "Xero-tenant-id": tenant_id,
        }
        url = f"{XERO_API_BASE_URL}/Accounts/{account_id}/Attachments/{file_name}"
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.put(url, content=file_content, headers=headers)
        if response.status_code not in {200, 201}:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json() if response.text else {"status": "success"}


xero_accounts_service = XeroAccountsService()
