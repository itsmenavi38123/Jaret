# backend/app/services/benchmark_service.py
"""
Benchmark Service
Fetches and caches financial benchmark (vs peers) data globally.
Cache TTL: 30 days, shared across all users.
"""
import json
import logging
import re
from typing import Any, Dict, Optional
from openai import AsyncOpenAI

from app.services.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# 30 days in seconds
BENCHMARK_CACHE_TTL = 30 * 24 * 60 * 60

# Expected benchmark metrics
BENCHMARK_METRICS = {
    "dso",
    "dpo",
    "inventory_turnover",
    "cash_conversion_cycle",
    "current_ratio",
    "quick_ratio",
    "debt_to_equity",
    "interest_coverage",
    "revenue_growth_rate",
    "net_profit_margin",
    "operating_cash_flow_margin",
    "cash_runway",
}

openai_client = AsyncOpenAI()


class BenchmarkService:
    """
    Service for fetching and caching financial benchmarks.
    
    Benchmarks are:
    - Fetched once and cached globally (30 days)
    - Keyed by business_type, country, revenue_band
    - Returned as JSON with p25, median, p75, source for each metric
    """

    def _calculate_revenue_band(self, annual_revenue_dollars: Optional[float]) -> Optional[int]:
        """
        Calculate revenue band from annual revenue.
        
        Returns revenue band (1-5) or None if revenue is missing.
        
        Band logic:
        - 1: < $500k
        - 2: $500k - $1M
        - 3: $1M - $5M
        - 4: $5M - $10M
        - 5: > $10M
        """
        if annual_revenue_dollars is None:
            return None
        
        if annual_revenue_dollars < 500_000:
            return 1
        elif annual_revenue_dollars < 1_000_000:
            return 2
        elif annual_revenue_dollars < 5_000_000:
            return 3
        elif annual_revenue_dollars < 10_000_000:
            return 4
        else:
            return 5

    def _build_cache_key(
        self,
        business_type: str,
        country: str,
        revenue_band: int,
    ) -> str:
        """
        Build cache key for benchmark data.
        
        Format: benchmark:{business_type}:{country}:{revenue_band}:national
        """
        return f"benchmark:{business_type.lower()}:{country.upper()}:{revenue_band}:national"

    def _safe_parse_json(self, content: str) -> Dict[str, Any]:
        """
        Safely parse JSON from AI response.
        
        Handles:
        - json\n{...}
        - ```json {...} ```
        - Extra whitespace
        
        Raises ValueError if JSON is invalid.
        """
        try:
            return json.loads(content)

        except json.JSONDecodeError:
            try:
                content = content.strip()
                content = re.sub(r"^```json", "", content)
                content = re.sub(r"^```", "", content)
                content = re.sub(r"^json", "", content)
                content = content.replace("```", "")
                content = content.strip()
                return json.loads(content)

            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON from AI: {content}") from exc

    async def _fetch_benchmarks_from_ai(
        self,
        business_type: str,
        country: str,
        revenue_band: int,
    ) -> Dict[str, Any]:
        """
        Fetch benchmark data from OpenAI.
        
        Returns JSON with 12 metrics:
        {
          "dso": {"p25": ..., "median": ..., "p75": ..., "source": "..."},
          ...
        }
        
        Each metric field (p25, median, p75) can be null if not found.
        """
        prompt = f"""
You are a financial benchmark expert. Fetch industry benchmark data for the following:

Business Type: {business_type}
Country: {country}
Revenue Band: {revenue_band} (where 1=<$500k, 2=$500k-$1M, 3=$1M-$5M, 4=$5M-$10M, 5=>$10M)

Return ONLY valid JSON with these 12 metrics. For each metric, return p25, median, p75, and source.
If a metric cannot be found, return null for that metric.

STRICT RULES:
- Return ONLY JSON (no explanation text)
- Use realistic industry benchmark estimates if exact data is not available
- Provide reasonable ranges (p25, median, p75)
- Never return all null values
- Each metric must have: p25, median, p75, source

METRICS TO FETCH:
1. dso (Days Sales Outstanding, in days)
2. dpo (Days Payable Outstanding, in days)
3. inventory_turnover (times per year)
4. cash_conversion_cycle (in days)
5. current_ratio (unitless)
6. quick_ratio (unitless)
7. debt_to_equity (ratio)
8. interest_coverage (times)
9. revenue_growth_rate (percentage, e.g., 5.2)
10. net_profit_margin (percentage, e.g., 10.5)
11. operating_cash_flow_margin (percentage, e.g., 12.3)
12. cash_runway (months for SMB, assume critical if not found)

RESPONSE FORMAT (ONLY JSON, no other text):
{{
  "dso": {{"p25": null, "median": null, "p75": null, "source": null}},
  "dpo": {{"p25": null, "median": null, "p75": null, "source": null}},
  "inventory_turnover": {{"p25": null, "median": null, "p75": null, "source": null}},
  "cash_conversion_cycle": {{"p25": null, "median": null, "p75": null, "source": null}},
  "current_ratio": {{"p25": null, "median": null, "p75": null, "source": null}},
  "quick_ratio": {{"p25": null, "median": null, "p75": null, "source": null}},
  "debt_to_equity": {{"p25": null, "median": null, "p75": null, "source": null}},
  "interest_coverage": {{"p25": null, "median": null, "p75": null, "source": null}},
  "revenue_growth_rate": {{"p25": null, "median": null, "p75": null, "source": null}},
  "net_profit_margin": {{"p25": null, "median": null, "p75": null, "source": null}},
  "operating_cash_flow_margin": {{"p25": null, "median": null, "p75": null, "source": null}},
  "cash_runway": {{"p25": null, "median": null, "p75": null, "source": null}}
}}
"""

        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial benchmark expert. Return ONLY valid JSON.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            benchmarks = self._safe_parse_json(content)

            # Validate that we got all expected metrics
            for metric in BENCHMARK_METRICS:
                if metric not in benchmarks:
                    benchmarks[metric] = {"p25": None, "median": None, "p75": None, "source": None}

            return benchmarks

        except Exception as exc:
            logger.error(f"Failed to fetch benchmarks from AI: {exc}")
            raise ValueError(f"AI benchmark fetch failed: {exc}") from exc

    async def get_or_fetch_benchmarks(
        self,
        business_type: str,
        country: str,
        annual_revenue_dollars: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """
        Get benchmark data from cache or fetch from AI if not cached.
        
        Args:
            business_type: Type of business (e.g., "retail", "saas", "consulting")
            country: Country code (e.g., "US", "CA", "UK")
            annual_revenue_dollars: Annual revenue in dollars (optional)
        
        Returns:
            Dict with 12 metrics, each with p25, median, p75, source
            Returns None if revenue is missing or benchmark fetch fails
        
        Flow:
        1. Calculate revenue band from annual_revenue_dollars
        2. Build cache key
        3. Check Redis cache
        4. If not cached, fetch from AI and store in Redis (TTL=30 days)
        5. Return data
        """
        # Skip if revenue is missing
        if annual_revenue_dollars is None:
            logger.warning("Skipping benchmark fetch: annual_revenue_dollars is None")
            return None

        # Calculate revenue band
        revenue_band = self._calculate_revenue_band(annual_revenue_dollars)
        if revenue_band is None:
            logger.warning("Failed to calculate revenue band")
            return None

        # Build cache key
        cache_key = self._build_cache_key(business_type, country, revenue_band)

        # Try to get from cache
        redis_client = await get_redis_client()
        if redis_client is not None:
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.info(f"Benchmark cache hit: {cache_key}")
                    return json.loads(cached)
            except Exception as exc:
                logger.warning(f"Redis get failed: {exc}. Proceeding with AI fetch.")

        # Not in cache, fetch from AI
        try:
            logger.info(f"Fetching benchmarks from AI: {cache_key}")
            benchmarks = await self._fetch_benchmarks_from_ai(business_type, country, revenue_band)

            # Store in Redis cache
            if redis_client is not None:
                try:
                    await redis_client.setex(
                        cache_key,
                        BENCHMARK_CACHE_TTL,
                        json.dumps(benchmarks),
                    )
                    logger.info(f"Benchmark cached: {cache_key}")
                except Exception as exc:
                    logger.warning(f"Failed to cache benchmark in Redis: {exc}")

            return benchmarks

        except Exception as exc:
            logger.error(f"Failed to get benchmarks: {exc}")
            return None


# Singleton instance
benchmark_service = BenchmarkService()
