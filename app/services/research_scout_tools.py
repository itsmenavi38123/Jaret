import json
from anthropic import beta_async_tool

from app.services.firecrawl_service import firecrawl_service


@beta_async_tool
async def firecrawl_search_tool(
    query: str,
    recency_days: int = 30,
    max_results: int = 10,
):
    """
    Search the web for real-time information about opportunities,
    events, market data, benchmarks, pricing, labor rates,
    industry trends, and business intelligence using Firecrawl.
    """

    res = await firecrawl_service.search(
        query=query,
        recency_days=recency_days,
        max_results=max_results,
    )
    return json.dumps(res, default=str)


@beta_async_tool
async def firecrawl_scrape_tool(
    url: str,
):
    """
    Scrape a URL and return parsed page content for deeper
    opportunity verification, benchmark validation,
    pricing research, and source analysis.
    """

    res = await firecrawl_service.scrape(
        url=url,
    )
    return json.dumps(res, default=str)