import httpx
from fastapi import HTTPException
from app.config import settings

# Xero OAuth2 endpoints
AUTH_BASE_URL = "https://login.xero.com/identity/connect/authorize"
TOKEN_URL = "https://identity.xero.com/connect/token"

# Build the authorization URL
def get_authorization_url(state: str = None):
    """
    Generate the Xero OAuth2 authorization URL
    """
    scope = "offline_access openid profile email accounting.transactions accounting.settings accounting.contacts"
    url = (
        f"{AUTH_BASE_URL}?"
        f"response_type=code"
        f"&client_id={settings.xero_client_id}"
        f"&redirect_uri={settings.xero_redirect_uri}"
        f"&scope={scope}"
        f"&state={state if state else 'secureRandomState123'}"
    )
    return url

# Exchange authorization code for tokens
async def exchange_code_for_tokens(code: str):
    """
    Exchange the authorization code for access and refresh tokens
    """
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.xero_redirect_uri,
        "client_id": settings.xero_client_id,
        "client_secret": settings.xero_client_secret,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(TOKEN_URL, data=data, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()