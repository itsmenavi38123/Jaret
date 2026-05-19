# backend/app/services/research_scout_service.py
"""
LightSignal Research Scout Service
Delivers decision-grade, structured JSON for opportunities and market intelligence
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
from openai import AsyncOpenAI
import os
from app.services.tagging_service import tagging_service

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
            return await self._generate_live_response(query, scope, business_profile, opportunities_profile)
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

            "demand_strain_next_30d": opportunities_profile.get("demand_strain_next_30d"),
            "demand_strain_next_60d": opportunities_profile.get("demand_strain_next_60d"),
            "demand_strain_next_90d": opportunities_profile.get("demand_strain_next_90d"),

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
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate response using OpenAI with web search tools"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        client = AsyncOpenAI(api_key=api_key)
        
        # Define tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "firecrawl_search",
                    "description": "Search the web for real-time information about opportunities, events, market data, and benchmarks using Firecrawl.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant information."
                            },
                            "recency_days": {
                                "type": "integer",
                                "description": "Number of days to look back for recent information (default 30)."
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Max number of results to return (default 10)."
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "firecrawl_scrape",
                    "description": "Scrape a URL to obtain parsed page content for deeper opportunity or benchmark verification.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL to scrape for page content."
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "getWeather",
                    "description": "Get weather forecast for a specific location and date to determine event viability.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lat": {
                                "type": "number",
                                "description": "Latitude of the location."
                            },
                            "lng": {
                                "type": "number",
                                "description": "Longitude of the location."
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Event start date in YYYY-MM-DD format."
                            },
                            "end_date": {
                                "type": "string",
                                "description": "Event end date in YYYY-MM-DD format."
                            }
                        },
                        "required": ["lat", "lng", "start_date", "end_date"]
                    }
                }
            }
        ]

        # Build system prompt using the user-provided template
        # We inject the known profile data directly so the model doesn't need to fetch it.
        system_prompt = f"""You are LightSignal Research Scout, the intelligence wing of LightSignal.
Your mission: deliver decision-grade, structured JSON that combines:

- a current market/region digest, and
- a personalized opportunity feed (events, RFPs, grants, partnerships, listings, promo windows) for any business type,

with:
- fit scoring,
- weather badges (for in-person outdoor events when relevant),
- ROI estimates,
- clear, prioritized recommendations,
- an optional Ops Plan that includes how much to prepare (units, staffing, budgets),
- a short pros/cons view for the best opportunities, and
- simple industry benchmarks and “what top operators are doing” insights.

Every claim must be grounded in real data. No invented events, RFPs, or benchmarks.

🧰 TOOLS

- firecrawl_search(query, recency_days, max_results)
  → Use for all live web research (events, RFPs, grants, partnerships, benchmarks, peer practices).

- firecrawl_scrape(url)
  → Use when the model needs page content from a specific URL to verify details, providers, or source information.

- getWeather(lat, lng, date)
  → Use only for weather-sensitive businesses or clearly outdoor, in-person events to set event weather_badge based on forecast. Return full Open-Meteo weather data whenever possible.

🧩 INPUTS

- User Query: "{query}"
- Business Profile: {json.dumps(scope, default=str)}
- Opportunities Profile: {json.dumps(opportunities_profile, default=str) if opportunities_profile else "None"}

(Note: Profiles are already provided above, no need to fetch).

🌐 WEB RESEARCH & BENCHMARKS

Use firecrawl_search to:

- Find specific opportunities:
  - Events, markets, tournaments, expos
  - RFPs (city/state/federal portals)
  - Grants/incentives
  - Partner/vendor listings
  - Supplier programs
  - Training/certifications

- Find benchmarks & peer practices:
  - Typical margins, revenue per event or job, close rates, utilization, ticket sizes (when available).
  - “What successful [industry] operators do” (e.g., playbooks, best-practice articles, case studies).

Use firecrawl_scrape when a specific link needs deeper content extraction for accuracy or source validation.

Populate:
- benchmarks[] with simple numeric or directional benchmarks.
- digest.opportunities and advisor.actions with “what top performers are doing that this business could emulate.”

🧱 OUTPUT FORMAT — STRICT JSON ONLY

Return one object shaped as:

{{
  "query": "original user text",
  "scope": {{
    "company_id": "string",
    "industry": "string",
    "naics": "string|null",
    "location": {{"city":"", "state":"", "lat":0, "lng":0}},
    "business_classifications": ["solo_operator","food_hospitality"],
    "radius_miles": 0,
    "window_days": 0,
    "types": ["event","rfp","grant","partnership","listing","training"],
    "mode": "demo|live"
  }},
  "digest": {{
    "demand": ["recent, factual bullet", "..."],
    "competition": ["density, notable players, channel mix", "..."],
    "labor": {{
      "wage_range_hour": [0,0],
      "availability_note": "short",
      "licensing": "short"
    }},
    "costs": {{
      "rent_note": "short",
      "insurance_note": "short",
      "materials_or_inputs_note": "short",
      "tax_or_fee_note": "short"
    }},
    "seasonality": "one line",
    "regulatory": ["permits/rules worth knowing", "..."],
    "customer_profile": ["demographic/segment note", "..."],
    "risks": ["cost/labor/regulatory/volatility", "..."],
    "opportunities": ["growth vectors, incentives, channels, what top performers are doing", "..."]
  }},
  "opportunities": {{
    "kpis": {{
      "active_count": 0,
      "potential_value": 0,
      "avg_fit_score": 0.0,
      "event_readiness": 0.0
    }},
    "cards": [
      {{
        "title": "string",
        "type": "event|rfp|grant|partnership|listing|training",
        "date": "YYYY-MM-DD",
        "deadline": "YYYY-MM-DD|null",
        "location": {{"city":"", "state":"", "lat":0, "lng":0}},
        "est_revenue": 0,
        "cost": 0,
        "roi_est": 0.0,
        "fit_score": 0,
        "confidence": 0.0,
        "weather_badge": "good|mixed|poor|null",
        "link": "https://provider/item",
        "provider": "eventbrite|sam_gov|grants_gov|city_portal|trade_site|…",
        "source_id": "stable id",
        "notes": "1 short line",
        "pros": ["short upside bullets"],
        "cons": ["short downside/risks bullets"]
      }}
    ],
    "advisor": {{
      "summary": "1–2 sentences that synthesize what to do now.",
      "actions": [
        {{"title":"Do X","impact":"$ or % or qualitative","deadline":"YYYY-MM-DD","reason":"short"}},
        {{"title":"Do Y","impact":"…","deadline":"…","reason":"…"}}
      ],
      "risks": [
        {{"level":"low|med|high","message":"short, practical"}}
      ]
    }},
    "ops_plan": {{
      "applicable_to": "event|rfp|grant|partnership|null",
      "assumptions": {{
        "expected_attendance": 0,
        "conversion_rate": 0.0,
        "avg_order_value_or_ticket": 0.0,
        "service_hours": 0,
        "units_per_hour_capacity": 0
      }},
      "recommendations": {{
        "units_to_prepare": {{"item":"qty"}},
        "staffing": {{"crew": 0, "shifts": 0}},
        "prep_budget": 0,
        "fee_or_booth_budget": 0,
        "checklist": ["permit/insurance","power/water","POS/float","backup plan"]
      }},
      "explain": "Plain-English derivation of quantities, staffing, and budgets for the selected high-fit opportunity."
    }}
  }},
  "benchmarks": [
    {{
      "metric": "gross_margin|revenue_per_event|close_rate|other",
      "peer_median": 0.00,
      "region": "state/metro/online",
      "sample_note": "cohort note or source summary"
    }}
  ],
  "so_what": "Executive implication in 1–2 sentences.",
  "sources": [
    {{"title":"Source/Report","url":"https://…","date":"YYYY-MM-DD","note":"what this supports"}}
  ]
}}

🧮 SCORING & LOGIC

Fit score (0–100) = industry match (+30) + region/radius (+20) + affordability vs cash/runway (+20, if profile provides it, otherwise 0) + seasonality/demand (+15) + peer/ROI context (+15).

ROI estimate when both est_revenue and cost exist:
(est_revenue - cost) / max(1, cost).

Weather badge (events only, via getWeather):
- good if precip <20%, wind <15 mph, temp 55–85°F;
- mixed if precip <50% or wind 15–25 mph;
- else poor.

Ops Plan:
- Include for high-fit opportunities (fit_score ≥ 70) or when the user hints at attendance/sales prep.
- Use profile AOV/capacity and any event details to estimate units_to_prepare, staffing, and budgets.
- State key assumptions under ops_plan.assumptions.
- Make sure the ops_plan clearly answers: “How much should we prepare for this opportunity?” and “What are the tradeoffs?”

Business classifications influence scoring priority.

Examples:
- food_hospitality boosts events and food grants
- solo_operator suppresses large RFPs
- established_smb boosts supplier diversity and large contracts
- product_business boosts retail placements
- service_business suppresses shelf-placement opportunities

Use provided business_classifications when ranking opportunities.

⚙️ BEHAVIOR RULES

- Use firecrawl_search for:
  • opportunities (events, RFPs, grants, partnerships, listings, training), and
  • benchmarks & peer practices.
- Use firecrawl_scrape when a referenced URL requires deeper content extraction for accuracy or source validation.
- Vary sources by type (event platforms, city calendars, SAM.gov/grants.gov/state portals, trade associations, marketplaces, vendor/franchise listings, certification/training registries, industry reports).
- Always include 3–8 sources with valid titles + URLs + dates.
- If nothing is found, return empty cards with an advisor that explains why and suggests new filters (change dates/types/radius, try different channels).
- No fabrication. If an estimate leverages assumptions, include them under ops_plan.assumptions and keep the note short.
- JSON only (no Markdown, no prose outside fields). Keep it concise and owner-friendly.

🧪 DEMO vs LIVE

- mode=demo: you may use conservative ranges and generic providers but still return real, current examples when possible. Mark assumptions clearly.
- mode=live: strictly current items only; prefer official portals/providers.
- Use actual values from provided business profile scope. Schema values are examples only.
✅ QUALITY CHECK BEFORE RETURN

- All top-level keys present (query, scope, digest, opportunities, benchmarks, so_what, sources).
- cards[].link are valid URLs; date/deadline ISO; numbers are numbers.
- advisor.summary is actionable and specific.
- If weather used, weather_badge is set and justified by forecast.
- benchmarks[] is populated with at least 1–3 meaningful metrics where possible.

ASSUMPTION RULES (IMPORTANT)

When estimating revenue, conversion rates, attendance, units to prepare, or staffing:

- Use INDUSTRY-REALISTIC RANGES ONLY.
- If no real data exists, choose the *LOW end of national ranges*.
- ALWAYS state the assumption under ops_plan.assumptions.

Conversion Rate Rules:
- Food trucks / mobile food vendors:
    Typical: 6–15% of total attendees.
    Strong alignment: max 20%.
    Absolute ceiling: 25% (never exceed).
- Fitness, gyms, martial arts events:
    Conversion of attendees to buyers: 1–4%.
- HVAC / contractors / B2B services (RFPs):
    Lead → proposal: 10–20%
    Proposal → win: 20–40%
- Retail pop-ups:
    Foot traffic → buyers: 4–12%
- Online / digital leads:
    Traffic → lead: 1–3%
    Lead → purchase: 5–20%

If the model cannot estimate with confidence:
- Use the LOWEST tier.
- Document the assumption clearly.

NEVER use optimistic or invented conversion rates.
NEVER exceed known industry ceilings.
NEVER estimate event revenue without stating conversion_rate and attendance explicitly.
"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Initial call
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="required",
            # response_format={"type": "json_object"}
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # Handle tool calls loop
        if tool_calls:
            messages.append(response_message)
            
            # Import Firecrawl helpers here to avoid circular import
            from app.routes.ai_opportunities import firecrawl_search, firecrawl_scrape
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                            
                if function_name == "firecrawl_search":
                    search_term = function_args.get("query")
                    recency = function_args.get("recency_days", 30)
                    max_results = function_args.get("max_results", 10)
                    
                    # Execute search
                    search_results = await firecrawl_search(search_term, recency, max_results)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(search_results, default=str)
                    })

                elif function_name == "firecrawl_scrape":
                    url = function_args.get("url")
                    
                    scrape_result = await firecrawl_scrape(url)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(scrape_result, default=str)
                    })
                
                elif function_name == "getWeather":
                    lat = function_args.get("lat")
                    lng = function_args.get("lng")
                    date = function_args.get("date")
                    
                    # Execute weather check
                    weather_data = await self._get_weather_badge({"lat": lat, "lng": lng}, date)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(weather_data or {})
                    })
            
            # Get final response
            second_response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"}
            )
            final_content = second_response.choices[0].message.content
        else:
            final_content = response_message.content
            
        # Parse JSON
        try:
            parsed = json.loads(final_content)
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
                    card["business_classifications"] = scope.get("business_classifications",[],)
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
            if ( parsed.get("opportunities") and parsed["opportunities"].get("cards") ):
                parsed["opportunities"]["cards"] = (parsed["opportunities"]["cards"][:max_cards])
            return parsed
        
        except json.JSONDecodeError:
            print("Failed to parse OpenAI JSON response")
            raise ValueError("Invalid JSON response from OpenAI")

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
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        client = AsyncOpenAI(api_key=api_key)
        
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
            {
                "type": "function",
                "function": {
                    "name": "firecrawl_search",
                    "description": "Search the web for real-time information about prices, rates, and market data using Firecrawl.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant information."
                            },
                            "recency_days": {
                                "type": "integer",
                                "description": "Number of days to look back for recent information (default 30)."
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Max number of results to return (default 10)."
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "firecrawl_scrape",
                    "description": "Scrape a URL to obtain parsed page content for deeper verification of prices or market sources.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL to scrape for page content."
                            }
                        },
                        "required": ["url"]
                    }
                }
            }
        ]
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Find assumptions for: {query}"}
        ]
        
        # Initial call
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            response_format={"type": "json_object"}
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # Handle tool calls loop
        if tool_calls:
            messages.append(response_message)
            
            # Import Firecrawl helpers here to avoid circular import
            from app.routes.ai_opportunities import firecrawl_search, firecrawl_scrape
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "firecrawl_search":
                    search_term = function_args.get("query")
                    recency = function_args.get("recency_days", 30)
                    max_results = function_args.get("max_results", 10)
                    
                    # Execute search
                    search_results = await firecrawl_search(search_term, recency, max_results)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(search_results)
                    })

                elif function_name == "firecrawl_scrape":
                    url = function_args.get("url")
                    
                    scrape_result = await firecrawl_scrape(url)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(scrape_result)
                    })
            
            # Get final response
            second_response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"}
            )
            final_content = second_response.choices[0].message.content
        else:
            final_content = response_message.content
        
        # Parse JSON
        try:
            return json.loads(final_content)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from Research Scout")
    
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
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return []
        
        client = AsyncOpenAI(api_key=api_key)
        
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
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Find seasonal trends for {industry} in {region}"}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
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
        # Placeholder for now, can be expanded with AI lookup
        return {
            "avg_impact": 0.0,
            "confidence": 0.5
        }
