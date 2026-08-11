import httpx
from typing import Dict, Any, List, Optional
from app.config import settings

class FacebookService:
    def __init__(self):
        self.client_id = settings.facebook_client_id
        self.client_secret = settings.facebook_client_secret
        self.default_redirect_uri = settings.facebook_redirect_uri
        self.config_id = settings.facebook_config_id
        self.graph_version = "v12.0"

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """Generate Facebook OAuth URL (Facebook Login for Business config)."""
        redirect = redirect_uri or self.default_redirect_uri
        scopes = "pages_show_list,pages_read_engagement"
        return (
            f"https://www.facebook.com/{self.graph_version}/dialog/oauth?"
            f"client_id={self.client_id}&"
            f"redirect_uri={redirect}&"
            f"state={state}&"
            f"scope={scopes}&"
            f"config_id={self.config_id}"
        )

    async def exchange_code_for_user_token(self, code: str, redirect_uri: Optional[str] = None) -> str:
        """Exchange auth code for a short-lived user access token."""
        redirect = redirect_uri or self.default_redirect_uri
        url = (
            f"https://graph.facebook.com/{self.graph_version}/oauth/access_token?"
            f"client_id={self.client_id}&"
            f"redirect_uri={redirect}&"
            f"client_secret={self.client_secret}&"
            f"code={code}"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data["access_token"]

    async def get_long_lived_user_token(self, short_lived_token: str) -> str:
        """Exchange short-lived user token for a long-lived user token."""
        url = (
            f"https://graph.facebook.com/{self.graph_version}/oauth/access_token?"
            f"grant_type=fb_exchange_token&"
            f"client_id={self.client_id}&"
            f"client_secret={self.client_secret}&"
            f"fb_exchange_token={short_lived_token}"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data["access_token"]

    async def get_user_pages(self, long_lived_user_token: str) -> List[Dict[str, Any]]:
        """Retrieve user's managed Facebook Pages and their Page Access Tokens."""
        url = f"https://graph.facebook.com/{self.graph_version}/me/accounts?access_token={long_lived_user_token}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    async def revoke_permissions(self, access_token: str) -> bool:
        """Revoke Facebook App permissions (disconnect app access)."""
        url = f"https://graph.facebook.com/{self.graph_version}/me/permissions?access_token={access_token}"
        async with httpx.AsyncClient() as client:
            response = await client.delete(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
            return False

    async def get_page_photos(self, page_id: str, page_access_token: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve uploaded photos from the Facebook Page."""
        url = (
            f"https://graph.facebook.com/{self.graph_version}/{page_id}/photos?"
            f"type=uploaded&fields=id,images,name,created_time&limit={limit}&"
            f"access_token={page_access_token}"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []

    async def download_image_as_base64(self, image_url: str) -> Optional[str]:
        """Download an image from a URL and return it as a base64 encoded string."""
        import base64
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(image_url)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode("utf-8")
        return None

facebook_service = FacebookService()
