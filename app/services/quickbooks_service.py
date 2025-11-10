import httpx
import base64
from fastapi import HTTPException
from app.config import settings

# Intuit OAuth2 endpoints
AUTH_BASE_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

# Build the authorization URL
def get_authorization_url(state: str = None, redirect_uri: str = None):
    scope = "com.intuit.quickbooks.accounting openid profile email"
    # Use provided redirect_uri or fall back to configured one
    callback_uri = redirect_uri if redirect_uri else settings.quickbooks_redirect_uri
    url = (
        f"{AUTH_BASE_URL}?client_id={settings.quickbooks_client_id}"
        f"&redirect_uri={callback_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state if state else 'secureRandomState123'}"
    )
    return url


# Exchange authorization code for tokens
async def exchange_code_for_tokens(code: str, redirect_uri: str = None):
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{settings.quickbooks_client_id}:{settings.quickbooks_client_secret}".encode()).decode(),
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    # Use provided redirect_uri or fall back to configured one
    callback_uri = redirect_uri if redirect_uri else settings.quickbooks_redirect_uri
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback_uri,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(TOKEN_URL, data=data, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()
