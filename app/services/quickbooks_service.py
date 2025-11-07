import httpx
import base64
from fastapi import HTTPException
from app.config import settings

# Intuit OAuth2 endpoints
AUTH_BASE_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

# Build the authorization URL
def get_authorization_url(state: str = None):
    scope = "com.intuit.quickbooks.accounting openid profile email"
    url = (
        f"{AUTH_BASE_URL}?client_id={settings.quickbooks_client_id}"
        f"&redirect_uri={settings.quickbooks_redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state if state else 'secureRandomState123'}"
    )
    return url


# Exchange authorization code for tokens
async def exchange_code_for_tokens(code: str):
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{settings.quickbooks_client_id}:{settings.quickbooks_client_secret}".encode()).decode(),
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.quickbooks_redirect_uri,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(TOKEN_URL, data=data, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()
