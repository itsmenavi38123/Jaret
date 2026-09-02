# backend/app/services/research_scout_service.py
"""
LightSignal Research Scout Service
Delivers decision-grade, structured JSON for opportunities and market intelligence
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
import os
import re
from app.services.tagging_service import tagging_service
from app.services.claude_service import claude_service
from app.services.research_scout_tools import (
    firecrawl_search_tool,
    firecrawl_scrape_tool,
)
from app.services.research_scout_prompt import get_research_scout_prompt
from app.services.lightsignal_memory_tool import LightSignalMemoryTool, LightSignalAsyncMemoryTool
from app.tools.calculator_tool import calculator_tool

class ResearchScoutService:
    """
    Research Scout service that matches the OpenAI agent prompt structure.
    Returns strict JSON-only responses with opportunities, digest, benchmarks, and advisor.
    """
    
    def __init__(self):
        pass
    
    async def search_opportunities(
        self,
        query: str,
        user_id: str,
        business_profile: Optional[Dict[str, Any]] = None,
        opportunities_profile: Optional[Dict[str, Any]] = None,
        mode: str = "live",
        run_type: str = "on_demand",
    ) -> Dict[str, Any]:
        """
        Main Research Scout function that returns structured JSON matching the agent prompt.
        
        Args:
            query: User's search query
            user_id: User ID (company_id)
            business_profile: Business profile data
            opportunities_profile: Opportunities profile data
            mode: "demo" or "live"
        
        Returns:
            Structured JSON matching the Research Scout format
        """
        scope = self._assemble_scout_context( user_id, business_profile, opportunities_profile, mode)
        
        scope["run_type"] = run_type
        scope["user_query"] = query
        
        try:
            return await self._generate_live_response(query, user_id, scope, business_profile, opportunities_profile)
        except Exception as e:
            print(f"Live mode failed: {e}")
            # In a real production system, you might want a fallback here, 
            # but for this cleanup, we are removing the legacy manual fallback.
            raise e

    def _assemble_scout_context(
        self,
        user_id: str,
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
        mode: str,
    ) -> Dict[str, Any]:

        onboarding = business_profile.get("onboarding_data", {}) if business_profile else {}

        industry = onboarding.get("industry_description", "Unknown")
        naics = onboarding.get("naics_code")

        geo = onboarding.get("geo", {})

        location = {
            "city": geo.get("city", onboarding.get("city", "")),
            "state": geo.get("state", onboarding.get("state", "")),
            "lat": geo.get("latitude", 0),
            "lng": geo.get("longitude", 0),
        }

        types = opportunities_profile.get("preferred_opportunity_types", []) if opportunities_profile else []

        radius_miles = opportunities_profile.get("radius", 50) if opportunities_profile else 50

        try:
            monthly_revenue = float(onboarding.get("monthly_revenue", 0))
        except (ValueError, TypeError):
            monthly_revenue = 0

        try:
            monthly_expenses = float(onboarding.get("monthly_expenses", 0))
        except (ValueError, TypeError):
            monthly_expenses = 0

        monthly_profit = monthly_revenue - monthly_expenses

        business_classifications = self._build_business_classifications(onboarding)
        business_tags = tagging_service.extract_business_tags(onboarding)

        return {
            "company_id": user_id,

            "business_name": onboarding.get("business_name"),
            "legal_entity_type": onboarding.get("business_entity"),
            "years_in_business": onboarding.get("founded_date"),
            "business_classifications": business_classifications,
            "business_tags": business_tags,

            "industry": industry,
            "industry_description": onboarding.get("industry_description"),
            "naics": naics,

            "location": location,

            "business_keywords": onboarding.get("main_products", ""),
            "main_products": onboarding.get("main_products"),

            "strategic_mode": onboarding.get("current_priority", []),
            "priorities": onboarding.get("priorities", []),

            "staff_count": onboarding.get("full_time_employees"),
            "market_focus": onboarding.get("market_focus"),

            "monthly_revenue": monthly_revenue,
            "monthly_expenses": monthly_expenses,
            "monthly_profit": monthly_profit,
            "cash_balance": opportunities_profile.get("cash_balance", 0) if opportunities_profile else 0,
            "outstanding_ar": opportunities_profile.get("outstanding_ar", []) if opportunities_profile else [],
            "runway_trend": opportunities_profile.get("runway_trend", "stable") if opportunities_profile else "stable",

            "demand_strain_next_30d": opportunities_profile.get("demand_strain_next_30d") if opportunities_profile else None,
            "demand_strain_next_60d": opportunities_profile.get("demand_strain_next_60d") if opportunities_profile else None,
            "demand_strain_next_90d": opportunities_profile.get("demand_strain_next_90d") if opportunities_profile else None,
            "latest_demand_forecast": opportunities_profile.get("latest_demand_forecast") if opportunities_profile else None,

            "permits_and_licenses": opportunities_profile.get("permits_and_licenses", []) if opportunities_profile else [],

            "competitors": onboarding.get("competitors"),

            "goals_12_months": onboarding.get("goals_12_months"),
            "goals_3_years": onboarding.get("goals_3_years"),
            "long_term_vision": onboarding.get("long_term_vision"),

            "growth_limits": onboarding.get("growth_limits", []),

            "max_budget": opportunities_profile.get("max_budget") if opportunities_profile else None,
            "travel_range": opportunities_profile.get("travel_range") if opportunities_profile else None,
            "staffing_capacity": opportunities_profile.get("staffing_capacity") if opportunities_profile else None,
            "risk_appetite": opportunities_profile.get("risk_appetite") if opportunities_profile else None,
            "service_model": opportunities_profile.get("service_model") if opportunities_profile else None,
            "price_tier": opportunities_profile.get("price_tier") if opportunities_profile else None,
            "audience": opportunities_profile.get("audience") if opportunities_profile else None,
            "proven_capabilities": opportunities_profile.get("proven_capabilities", []) if opportunities_profile else [],
            "historical_outcomes": opportunities_profile.get("historical_outcomes", []) if opportunities_profile else [],
            
            "radius_miles": radius_miles,
            "window_days": 14,

            "types": types,
            "mode": mode,
        }
    def _build_business_classifications(
        self,
        onboarding: Dict[str, Any],
    ) -> List[str]:

        classifications = []

        industry = (
            onboarding.get("industry_description", "") or ""
        ).lower()

        naics = str(
            onboarding.get("naics_code", "") or ""
        )

        main_products = (
            onboarding.get("main_products", "") or ""
        ).lower()

        staff_count = onboarding.get("full_time_employees")

        try:
            staff_count = int(staff_count)
        except (TypeError, ValueError):
            staff_count = None

        if staff_count is not None:

            if staff_count <= 2:
                classifications.append("solo_operator")

            elif 3 <= staff_count <= 10:
                classifications.append("small_team")

            elif staff_count >= 10:
                classifications.append("established_smb")

        if (
            "food" in industry
            or "cafe" in industry
            or naics.startswith("722")
            or naics.startswith("311")
        ):
            classifications.append("food_hospitality")

        if (
            naics.startswith("236")
            or naics.startswith("237")
            or naics.startswith("238")
        ):
            classifications.append("trades_contractor")

        if (
            naics.startswith("541")
            or naics.startswith("561")
        ):
            classifications.append("professional_services")

        if "arts" in industry or "creative" in industry:
            classifications.append("creative_arts")

        if (
            naics.startswith("621")
            or naics.startswith("713")
            or naics.startswith("812")
        ):
            classifications.append("health_wellness")

        product_keywords = [
            "product",
            "retail",
            "packaged",
            "manufacturing",
            "goods",
            "coffee",
            "beverage",
            "food",
        ]

        is_product_business = any(
            keyword in main_products
            for keyword in product_keywords
        )

        if is_product_business:
            classifications.append("product_business")

        manufacturing_naics = (
            naics.startswith("31")
            or naics.startswith("32")
            or naics.startswith("33")
        )

        if (
            not is_product_business
            and "food" not in industry
            and not manufacturing_naics
        ):
            classifications.append("service_business")

        return list(set(classifications))

    async def _generate_live_response(
        self,
        query: str,
        user_id: str,
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate response using OpenAI with web search tools"""
                
        # Define tools
        memory_tool = LightSignalAsyncMemoryTool(user_id=user_id)
        tools = [
            memory_tool,
            calculator_tool,
            firecrawl_search_tool,
            firecrawl_scrape_tool,
        ]


        system_prompt = get_research_scout_prompt()

        user_payload = {
            "mode": "opportunity_discovery",
            "query": query,
            "business_profile": business_profile or scope,
            "opportunities_profile": opportunities_profile,
            "scope": scope,
        }
        user_content_str = json.dumps(user_payload, default=str)
        
        # Initial call
        response = await claude_service.tool_runner(
            system_prompt=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_content_str,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ],
                }
            ],
            tools=tools,
            temperature=0.2,
            max_tokens=8000,
        )

        final_content = ""

        for block in response.content:
            if getattr(block, "type", None) == "text":
                final_content += block.text
            
        # Parse JSON
        parsed = None
        try:
            cleaned = final_content.strip()
            cleaned = re.sub(r"^```json\s*", "", cleaned)
            cleaned = re.sub(r"^```\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end != -1:
                cleaned = cleaned[start:end]

            parsed = json.loads(cleaned)
        except Exception as e:
            print(f"Failed to parse Claude JSON response from tool_runner: {e}. Trying json_completion fallback...")
            try:
                parsed = await claude_service.json_completion(
                    system_prompt=system_prompt,
                    user_content=user_payload,
                    temperature=0.2,
                    max_tokens=4000,
                )
            except Exception as fb_err:
                print(f"Fallback json_completion also failed: {fb_err}")
                raise ValueError("Invalid JSON response from Claude")

        if not parsed or not isinstance(parsed, dict):
            raise ValueError("Invalid JSON response from Claude")

        if parsed.get("opportunities") and parsed["opportunities"].get("cards"):
            business_tags = scope.get("business_tags", [])

            for card in parsed["opportunities"]["cards"]:
                metadata = tagging_service.extract_full_opportunity_metadata(
                    title=card.get("title", ""),
                    notes=card.get("notes", ""),
                    opportunity_type=card.get("type", ""),
                )

                opportunity_tags = metadata.get("opportunity_tags", [])

                card["opportunity_tags"] = opportunity_tags
                card["business_tags"] = business_tags
                card["event_prestige_tier"] = metadata.get("event_prestige_tier")
                card["event_audience"] = metadata.get("event_audience")
                card["event_service_fit"] = metadata.get("event_service_fit", [])
                card["business_classifications"] = scope.get("business_classifications", [])
                card["service_model"] = scope.get("service_model")
                card["price_tier"] = scope.get("price_tier")
                card["audience"] = scope.get("audience")
                card["proven_capabilities"] = scope.get("proven_capabilities", [])
                card["historical_outcomes"] = scope.get("historical_outcomes", [])
                card["cash_balance"] = scope.get("cash_balance", 0)
                card["outstanding_ar"] = scope.get("outstanding_ar", [])
                card["runway_trend"] = scope.get("runway_trend", "stable")

                card["demand_strain_next_30d"] = scope.get("demand_strain_next_30d")
                card["demand_strain_next_60d"] = scope.get("demand_strain_next_60d")
                card["demand_strain_next_90d"] = scope.get("demand_strain_next_90d")
                card["latest_demand_forecast"] = scope.get("latest_demand_forecast")

                card["permits_and_licenses"] = scope.get("permits_and_licenses", [])

                card["industry_jaccard_score"] = tagging_service.calculate_jaccard_similarity(
                    business_tags,
                    opportunity_tags,
                )

                card["adjacent_match"] = tagging_service.has_adjacent_match(
                    business_tags,
                    opportunity_tags,
                )

        max_cards = 8 if scope.get("run_type") == "on_demand" else 12
        if parsed.get("opportunities") and parsed["opportunities"].get("cards"):
            parsed["opportunities"]["cards"] = parsed["opportunities"]["cards"][:max_cards]
        return parsed

    async def _get_weather_badge(
        self,
        location: Dict[str, Any],
        date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        if ( location.get("lat") is None or location.get("lng") is None):
            return None

        try:
            import httpx
            from datetime import datetime

            lat = location.get("lat")
            lng = location.get("lng")

            target_date = date if date else datetime.utcnow().strftime("%Y-%m-%d")

            url = "https://api.open-meteo.com/v1/forecast"

            params = {
                "latitude": lat,
                "longitude": lng,
                "daily": "precipitation_probability_max,temperature_2m_max,temperature_2m_min,weathercode,windspeed_10m_max",
                "start_date": target_date,
                "end_date": target_date,
                "timezone": "auto",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url,
                    params=params,
                )

            if response.status_code != 200:
                return None

            data = response.json()

            daily = data.get("daily", {})

            precipitation = daily.get(
                "precipitation_probability_max",
                [0],
            )[0]

            wind_speed = daily.get(
                "windspeed_10m_max",
                [0],
            )[0]

            temp_max = daily.get(
                "temperature_2m_max",
                [70],
            )[0]

            temp_min = daily.get(
                "temperature_2m_min",
                [60],
            )[0]

            weather_code = daily.get(
                "weathercode",
                [0],
            )[0]

            avg_temp = (temp_max + temp_min) / 2

            if 65 <= temp_max <= 80:
                comfort_score = 1.0
            elif 55 <= temp_max <= 64:
                comfort_score = 0.8
            elif 80 <= temp_max <= 90:
                comfort_score = 0.7
            elif 45 <= temp_max <= 54:
                comfort_score = 0.5
            elif 90 <= temp_max <= 100:
                comfort_score = 0.4
            else:
                comfort_score = 0.2

            severe_weather = False
            severe_description = None

            if weather_code >= 95:
                severe_weather = True
                severe_description = "Thunderstorm"
            elif weather_code >= 80:
                severe_weather = True
                severe_description = "Heavy Rain Showers"
            elif weather_code >= 73:
                severe_weather = True
                severe_description = "Heavy Snow"
            elif weather_code >= 65:
                severe_weather = True
                severe_description = "Heavy Rain"

            if (
                precipitation < 20
                and wind_speed < 15
                and 55 <= avg_temp <= 85
            ):
                weather_badge = "good"

            elif (
                precipitation < 50
                or (15 <= wind_speed <= 25)
            ):
                weather_badge = "mixed"

            else:
                weather_badge = "poor"

            return {
                "precipitation_probability": precipitation / 100,
                "temperature_max_f": temp_max,
                "temperature_min_f": temp_min,
                "temperature_comfort_score": comfort_score,
                "severe_weather_flag": severe_weather,
                "severe_weather_description": severe_description,
                "windspeed_mph": wind_speed,
                "weather_badge": weather_badge,
            }

        except Exception as e:
            print(f"Open-Meteo weather error: {e}")
            return None

    async def get_scenario_priors(
        self,
        scenario_type: str,
        query: str,
        business_profile: Optional[Dict[str, Any]] = None,
        classifier_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        
        """
        Get assumptions/priors for scenario planning using web search.
        
        Args:
            scenario_type: Type of scenario (CapEx, Hiring, Pricing, Expansion)
            query: User's scenario query
            business_profile: Business profile data
        
        Returns:
            Dict with assumptions[] and sources[]
        """
        
        # Extract industry from business profile
        industry = "Unknown"
        if business_profile and business_profile.get("onboarding_data"):
            onboarding = business_profile["onboarding_data"]
            industry = onboarding.get("industry", onboarding.get("business_type", "Unknown"))
        
        # Build system prompt for Research Scout (priors mode)
        system_prompt = f"""You are LightSignal Research Scout in Scenario Priors mode.

        Your mission: Fill missing assumptions for financial scenario planning using real web data.

        TOOLS

        - firecrawl_search(query, recency_days, max_results)
        → Use to find real-world data: equipment prices, interest rates, labor rates, market benchmarks.

        INPUTS

        - **Scenario Type**: {scenario_type}
        - **User Query**: "{query}"
        - **Industry**: {industry}
        - **Business Profile**: {json.dumps(business_profile, default=str) if business_profile else "None"}

        OUTPUT FORMAT — STRICT JSON ONLY

        Return one object shaped as:

        {{
        "assumptions": [
            {{
            "key": "equipment_cost",
            "value": 50000,
            "source": "https://valid-supplier.com/item",
            "confidence": 0.8
            }},
            {{
            "key": "labor_rate_hourly",
            "value": 25.0,
            "source": "https://bls.gov/wages",
            "confidence": 0.9
            }}
        ],
        "sources": [
            {{
            "title": "Equipment Pricing Guide 2024",
            "url": "https://valid-supplier.com/item",
            "date": "2024-01-15",
            "note": "Used for equipment cost estimates"
            }}
        ]
        }}

        BEHAVIOR RULES

        - **CRITICAL**: DO NOT USE 'example.com' or 'test.com'. If you cannot find a source, leave the source field null or omit the assumption.
        - Use firecrawl_search to find real data for ALL assumptions.
        - Use firecrawl_scrape when a specific source URL needs deeper content verification.
        - Common assumptions by scenario type:
        - **CapEx**: equipment_cost, financing_rate, useful_life_years, maintenance_cost_annual
        - **Hiring**: salary_annual, benefits_cost_pct, training_cost, productivity_ramp_months
        - **Pricing**: competitor_prices, price_elasticity, market_avg_price
        - **Expansion**: location_rent, build_out_cost, time_to_revenue_months
        - Always include sources with valid URLs.
        - Confidence should reflect data quality (0.0-1.0).
        - If data is not available, use industry averages and note the assumption.

        QUALITY CHECK BEFORE RETURN

        - At least 3-5 assumptions populated.
        - All assumptions have sources.
        - Sources have valid URLs (NO example.com).

        JSON only (no Markdown, no prose outside fields).
        """

        # Define tools
        tools = [
            calculator_tool,
            firecrawl_search_tool,
            firecrawl_scrape_tool,
        ]
        

        # Initial call

        response = await claude_service.tool_runner(
            system_prompt=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "query": query,
                            "classifier_output": classifier_output,
                        },
                        default=str,
                    ),
                }
            ],
            tools=tools,
            temperature=0.2,
            max_tokens=4000,
        )

        final_content = ""

        for block in response.content:
            if getattr(block, "type", None) == "text":
                final_content += block.text
        
        # Parse JSON
        try:
            return json.loads(final_content)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from Research Scout")
    
    async def investigate_watch_area(
        self,
        pattern: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> Dict[str, Any]:

        system_prompt = """
        You are Research Scout in WATCH_AREA_INVESTIGATION mode.

        Your job:
        Analyze a business watch-area pattern and identify realistic possible causes.

        CRITICAL RULES:
        - Use only provided payload information.
        - Never invent metrics or business entities.
        - Focus on operational/business causes.
        - Return grounded explanations.
        - Keep causes concise and practical.

        STRICT JSON ONLY

        {
        "mode": "watch_area_investigation",
        "pattern": {},
        "possible_causes": [
            {
            "cause": "string",
            "evidence": "string",
            "source_url": "string or null",
            "as_of": "string or null"
            }
        ]
        }
        """

        payload = {
            "mode": "watch_area_investigation",
            "pattern": pattern,
            "business_context": business_context,
        }

        try:
            return await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content=payload,
                temperature=0.2,
                max_tokens=2000,
            )

        except Exception:
            raise ValueError("Invalid JSON response from watch area investigation")

    async def get_peer_seasonal_trends(
        self,
        industry: str,
        region: str
    ) -> List[Dict[str, Any]]:
        """
        Get peer seasonal trends for demand forecasting.
        
        Args:
            industry: Industry name
            region: Region name
        
        Returns:
            List of peer trend objects
        """
        
        system_prompt = f"""You are LightSignal Research Scout.
Find seasonal trends for {industry} in {region}.
Return JSON with trends array:
{{
    "trends": [
        {{
            "metric": "revenue|traffic|conversion",
            "peer_median": 0.0,
            "region": "{region}",
            "trend": "growing|stable|declining",
            "source": "source name",
            "sample_note": "short note"
        }}
    ]
}}
"""
        
        try:
            result = await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content=f"Find seasonal trends for {industry} in {region}",
                temperature=0.2,
                max_tokens=2000,
            )

            return result.get("trends", [])

        except Exception as e:
            print(f"Error getting peer trends: {e}")
            return []
        
    async def get_event_impact_stats(
        self,
        event_type: str,
        industry: str
    ) -> Dict[str, Any]:
        """
        Get event impact statistics.
        
        Args:
            event_type: Type of event
            industry: Industry name
            
        Returns:
            Impact stats dictionary
        """
        return {
            "avg_impact": 0.0,
            "confidence": 0.5
        }

    async def investigate_watch_area(
        self,
        pattern: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Investigate a business pattern using Canonical Research Scout (MODE 2: WATCH AREA INVESTIGATION).
        Searches web/weather to find grounded real-world causes backed by evidence and URLs.
        """
        system_prompt = get_research_scout_prompt()
        
        try:
            return await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content={
                    "mode": "watch_area_investigation",
                    "pattern": pattern,
                    "business_context": business_context,
                },
                temperature=0.2,
                max_tokens=4000,
            )
        except Exception as e:
            print(f"Watch area investigation failed: {e}")
            return {
                "mode": "watch_area_investigation",
                "pattern": pattern,
                "possible_causes": [],
                "search_summary": {
                    "queries_run": [],
                    "sources_consulted": [],
                    "weather_checked": False,
                    "no_findings_explanation": f"Investigation could not complete: {e}"
                },
                "investigation_metadata": {
                    "investigation_id": "fallback",
                    "pattern_type": "internal_only",
                    "is_internal_pattern": True
                }
            }


# Singleton instance
research_scout_service = ResearchScoutService()

