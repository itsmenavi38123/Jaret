# backend/app/services/firecrawl_service.py

from typing import Dict, Any, List, Optional
import httpx
import os


class FirecrawlService:

    SEARCH_URL = "https://api.firecrawl.dev/v2/search"
    SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"

    def __init__(self):

        self.api_key = os.getenv("FIRECRAWL_API_KEY")

        if not self.api_key:
            raise ValueError(
                "FIRECRAWL_API_KEY not found in environment"
            )

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        recency_days: int = 30,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:

        if not query:
            return []

        combined_query = query

        if location:
            combined_query = f"{query} {location}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": combined_query,
            "limit": min(max_results, 10),
            "scrapeOptions": {
                "formats": ["markdown"]
            }
        }

        try:

            async with httpx.AsyncClient(timeout=30.0) as client:

                response = await client.post(
                    self.SEARCH_URL,
                    json=payload,
                    headers=headers,
                )

            if response.status_code != 200:

                print(
                    f"Firecrawl search error: "
                    f"{response.status_code}"
                )

                return []

            data = response.json()

            results = data.get("data", {}).get("web", [])

            formatted_results = []

            for item in results:

                formatted_results.append({
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "markdown": item.get("markdown"),
                })

            return formatted_results

        except Exception as e:

            print(f"Firecrawl search exception: {e}")

            return []

    async def scrape(
        self,
        url: str,
    ) -> Dict[str, Any]:

        if not url:
            return self._empty_scrape_response()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": False,
            "waitFor": 2000,
        }

        try:

            async with httpx.AsyncClient(timeout=45.0) as client:

                response = await client.post(
                    self.SCRAPE_URL,
                    json=payload,
                    headers=headers,
                )

            if response.status_code != 200:

                print(
                    f"Firecrawl scrape error: "
                    f"{response.status_code}"
                )

                return self._empty_scrape_response()

            data = response.json()

            scrape_data = data.get("data", {})

            return {
                "url": url,
                "markdown": scrape_data.get("markdown"),
                "metadata": scrape_data.get("metadata", {}),
                "success": True,
            }

        except Exception as e:

            print(f"Firecrawl scrape exception: {e}")

            return self._empty_scrape_response()

    def _empty_scrape_response(
        self
    ) -> Dict[str, Any]:

        return {
            "url": None,
            "markdown": None,
            "metadata": {},
            "success": False,
        }


firecrawl_service = FirecrawlService()