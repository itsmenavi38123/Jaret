# backend/app/services/benchmark_service.py
"""
Benchmark Service
Fetches and caches financial benchmark (vs peers) data globally.
Cache TTL: 30 days, shared across all users.
"""
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional
from openai import AsyncOpenAI

from app.db import get_collection
from app.services.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# 30 days in seconds
BENCHMARK_CACHE_TTL = 30 * 24 * 60 * 60
BENCHMARK_DEFAULT_SOURCE = "AI estimate"

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

BENCHMARK_METRIC_CONFIG = {
    "dso": {"direction": "lower"},
    "dpo": {"direction": "lower"},
    "inventory_turnover": {"direction": "higher"},
    "cash_conversion_cycle": {"direction": "lower"},
    "current_ratio": {"direction": "higher"},
    "quick_ratio": {"direction": "higher"},
    "debt_to_equity": {"direction": "lower"},
    "interest_coverage": {"direction": "higher"},
    "revenue_growth_rate": {"direction": "higher"},
    "net_profit_margin": {"direction": "higher"},
    "operating_cash_flow_margin": {"direction": "higher"},
    "cash_runway": {"direction": "higher"},
}

KPI_TO_BENCHMARK_METRIC = {
    "net_margin_pct": "net_profit_margin",
    "runway_months": "cash_runway",
    "quick_ratio": "quick_ratio",
    "current_ratio": "current_ratio",
    "inventory_turns": "inventory_turnover",
    "ccc_days": "cash_conversion_cycle",
    "dso_days": "dso",
    "revenue_growth_rate": "revenue_growth_rate",
}

DEFAULT_CLASSIFIER_FIELDS = ["industry", "country", "revenue_band"]

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

    def _normalize_metric_payload(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "p15": metric.get("p15"),
            "p35": metric.get("p35"),
            "p65": metric.get("p65"),
            "p85": metric.get("p85"),
            "median": metric.get("median"),
            "source": metric.get("source") or BENCHMARK_DEFAULT_SOURCE,
            "confidence": metric.get("confidence", 0.0),
            "citation": metric.get("citation", {"title": metric.get("source") or BENCHMARK_DEFAULT_SOURCE}),
            "peer_pool": metric.get("peer_pool"),
        }

    def linear_interp(self, x: float, x0: float, y0: float, x1: float, y1: float) -> float:
        if x0 == x1:
            return float((y0 + y1) / 2)
        return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)

    def score_to_label(self, score: Optional[float]) -> Optional[str]:
        if score is None:
            return None
        if score >= 85:
            return "top_tier"
        if score >= 65:
            return "above_average"
        if score >= 35:
            return "at_average"
        if score >= 15:
            return "below_average"
        return "critical"

    def apply_distress_override(
        self,
        metric_key: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if context is None:
            context = {}

        if metric_key == "cash_runway" and value is not None:
            try:
                if float(value) < 1:
                    return True
            except (TypeError, ValueError):
                pass

        if context.get("negative_working_capital") is True:
            return True

        if context.get("license_expired") is True:
            return True

        return False

    def _benchmark_metric_complete(self, benchmark_metric: Optional[Dict[str, Any]]) -> bool:
        if not benchmark_metric:
            return False
        return all(
            benchmark_metric.get(key) is not None
            for key in ("p15", "p35", "p65", "p85")
        )

    def metric_to_score(
        self,
        metric_key: str,
        metric_value: Any,
        benchmark_metric: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = {
            "score": None,
            "label": None,
            "percentile_band": None,
            "source": None,
            "is_ai_estimate": False,
            "citation": None,
            "distress_override": False,
            "missing_data_notice": None,
        }

        if metric_value is None:
            result["missing_data_notice"] = "Metric value unavailable. Benchmark scoring cannot be applied."
            return result

        if not self._benchmark_metric_complete(benchmark_metric):
            result["missing_data_notice"] = "Benchmark data unavailable. Benchmark scoring cannot be applied."
            return result

        direction = BENCHMARK_METRIC_CONFIG.get(metric_key, {}).get("direction", "higher")
        try:
            value = float(metric_value)
            p15 = float(benchmark_metric["p15"])
            p35 = float(benchmark_metric["p35"])
            p65 = float(benchmark_metric["p65"])
            p85 = float(benchmark_metric["p85"])
        except (TypeError, ValueError, KeyError):
            result["missing_data_notice"] = "Benchmark data invalid. Benchmark scoring cannot be applied."
            return result

        if direction == "higher":
            if value <= p15:
                score = 0.0
                band = "below_p15"
            elif value <= p35:
                score = self.linear_interp(value, p15, 0.0, p35, 25.0)
                band = "p15_p35"
            elif value <= p65:
                score = self.linear_interp(value, p35, 25.0, p65, 75.0)
                band = "p35_p65"
            elif value <= p85:
                score = self.linear_interp(value, p65, 75.0, p85, 100.0)
                band = "p65_p85"
            else:
                score = 100.0
                band = "above_p85"
        else:
            if value <= p15:
                score = 100.0
                band = "above_p85"
            elif value <= p35:
                score = self.linear_interp(value, p15, 100.0, p35, 75.0)
                band = "p15_p35"
            elif value <= p65:
                score = self.linear_interp(value, p35, 75.0, p65, 25.0)
                band = "p35_p65"
            elif value <= p85:
                score = self.linear_interp(value, p65, 25.0, p85, 0.0)
                band = "p65_p85"
            else:
                score = 0.0
                band = "below_p15"

        score = max(0, min(100, int(round(score))))
        label = self.score_to_label(score)
        source = benchmark_metric.get("source") or BENCHMARK_DEFAULT_SOURCE
        is_ai_estimate = isinstance(source, str) and source.strip().lower() == "ai estimate"
        citation = benchmark_metric.get("citation") or {}
        distress_override = self.apply_distress_override(metric_key, value, context)

        if distress_override:
            label = "critical"

        result.update({
            "score": score,
            "label": label,
            "percentile_band": band,
            "source": source,
            "is_ai_estimate": is_ai_estimate,
            "citation": citation,
            "distress_override": distress_override,
        })

        return result

    def _build_classifier(self, business_type: str, country: str, revenue_band: int) -> Dict[str, Any]:
        return {
            "industry": business_type,
            "country": country,
            "revenue_band": revenue_band,
        }

    def _build_classifier_query(self, classifier: Dict[str, Any]) -> Dict[str, Any]:
        return {f"classifier.{key}": value for key, value in classifier.items() if value is not None}

    async def _get_benchmarks_from_db(self, classifier: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not classifier:
            return None

        collection = get_collection("benchmarks")
        query = self._build_classifier_query(classifier)
        cursor = collection.find(query)
        docs = await cursor.to_list(length=None)

        if not docs:
            return None

        return {
            doc["metric_key"]: self._normalize_metric_payload(doc)
            for doc in docs
            if doc.get("metric_key")
        }

    async def _save_benchmarks_to_db(
        self,
        benchmarks: Dict[str, Any],
        classifier: Dict[str, Any],
        peer_pool: Dict[str, Any],
    ) -> None:
        collection = get_collection("benchmarks")
        now = datetime.utcnow()

        for metric_key, metric_payload in benchmarks.items():
            normalized = self._normalize_metric_payload(metric_payload)
            document = {
                "metric_key": metric_key,
                "classifier": classifier,
                "peer_pool": peer_pool,
                "percentile_bands": {
                    "p15": normalized["p15"],
                    "p35": normalized["p35"],
                    "p65": normalized["p65"],
                    "p85": normalized["p85"],
                },
                "median": normalized["median"],
                "source": normalized["source"],
                "as_of": now,
                "confidence": normalized["confidence"],
                "citation": normalized["citation"],
                "peer_pool": peer_pool,
                "raw": metric_payload,
                "updated_at": now,
            }
            query = {"metric_key": metric_key, **self._build_classifier_query(classifier)}
            await collection.update_one(query, {"$set": document}, upsert=True)

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
          "dso": {"p15": ..., "p35": ..., "p65": ..., "p85": ..., "median": ..., "source": ...},
          ...
        }
        """
        prompt = f"""
You are a financial benchmark expert. Fetch industry benchmark data for the following:

Business Type: {business_type}
Country: {country}
Revenue Band: {revenue_band} (where 1=<$500k, 2=$500k-$1M, 3=$1M-$5M, 4=$5M-$10M, 5=>$10M)

Return ONLY valid JSON with these 12 metrics. For each metric, return p15, p35, p65, p85, median, and source.
If a metric cannot be found, return null for that metric.

STRICT RULES:
- Return ONLY JSON (no explanation text)
- Use realistic industry benchmark estimates if exact data is not available
- Provide consistent percentiles for p15, p35, p65, and p85
- Never return all null values
- Each metric must have: p15, p35, p65, p85, median, source

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
  "dso": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "dpo": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "inventory_turnover": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "cash_conversion_cycle": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "current_ratio": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "quick_ratio": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "debt_to_equity": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "interest_coverage": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "revenue_growth_rate": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "net_profit_margin": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "operating_cash_flow_margin": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}},
  "cash_runway": {{"p15": null, "p35": null, "p65": null, "p85": null, "median": null, "source": null}}
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

            # Normalize expected metrics
            for metric in BENCHMARK_METRICS:
                if metric not in benchmarks:
                    benchmarks[metric] = {
                        "p15": None,
                        "p35": None,
                        "p65": None,
                        "p85": None,
                        "median": None,
                        "source": None,
                        "confidence": 0.0,
                        "citation": {"title": BENCHMARK_DEFAULT_SOURCE},
                    }
                else:
                    benchmarks[metric] = self._normalize_metric_payload(benchmarks[metric])

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

        classifier = self._build_classifier(business_type, country, revenue_band)
        peer_pool = {
            "industry": business_type,
            "geography": country,
            "size": revenue_band,
        }

        redis_client = await get_redis_client()
        if redis_client is not None:
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.info(f"Benchmark cache hit: {cache_key}")
                    data = json.loads(cached)
                    return data
            except Exception as exc:
                logger.warning(f"Redis get failed: {exc}. Falling back to DB.")

        benchmarks = await self._get_benchmarks_from_db(classifier)
        if benchmarks is not None:
            if redis_client is not None:
                try:
                    await redis_client.setex(cache_key, BENCHMARK_CACHE_TTL, json.dumps(benchmarks))
                except Exception as exc:
                    logger.warning(f"Failed to cache benchmark in Redis: {exc}")
            return benchmarks

        # Not in cache or DB, fetch from AI and persist permanently
        try:
            logger.info(f"Fetching benchmarks from AI: {cache_key}")
            benchmarks = await self._fetch_benchmarks_from_ai(business_type, country, revenue_band)
            await self._save_benchmarks_to_db(benchmarks, classifier, peer_pool)

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
