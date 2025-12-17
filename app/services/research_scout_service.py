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
        scope = self._build_scope(user_id, business_profile, opportunities_profile, mode)
        
        try:
            return await self._generate_live_response(query, scope, business_profile, opportunities_profile)
        except Exception as e:
            print(f"Live mode failed: {e}")
            # In a real production system, you might want a fallback here, 
            # but for this cleanup, we are removing the legacy manual fallback.
            raise e

    def _build_scope(
        self,
        user_id: str,
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
        mode: str,
    ) -> Dict[str, Any]:
        """Build scope object"""
        # Extract industry/NAICS from business profile
        industry = "Unknown"
        naics = None
        if business_profile and business_profile.get("onboarding_data"):
            onboarding = business_profile["onboarding_data"]
            industry = onboarding.get("industry", onboarding.get("business_type", "Unknown"))
            naics = onboarding.get("naics")
        
        # Extract location
        location = {"city": "", "state": "", "lat": 0, "lng": 0}
        if opportunities_profile:
            region = opportunities_profile.get("operating_region", "")
            if region:
                # Try to parse city/state
                parts = region.split(",")
                if len(parts) >= 2:
                    location["city"] = parts[0].strip()
                    location["state"] = parts[1].strip()
                else:
                    location["state"] = region
        
        # Extract types and radius
        types = opportunities_profile.get("preferred_opportunity_types", []) if opportunities_profile else []
        radius_miles = opportunities_profile.get("radius", 50) if opportunities_profile else 50
        
        return {
            "company_id": user_id,
            "industry": industry,
            "naics": naics,
            "location": location,
            "radius_miles": radius_miles,
            "window_days": 14,  # Default 2-week window
            "types": types,
            "mode": mode,
        }

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
                    "name": "search_web",
                    "description": "Search the web for real-time information about opportunities, events, market data, and benchmarks.",
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
                            "date": {
                                "type": "string",
                                "description": "Date of the event (YYYY-MM-DD)."
                            }
                        },
                        "required": ["lat", "lng"]
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

- search_web(query, recency_days, max_results)
  → Use for all live web research (events, RFPs, grants, partnerships, benchmarks, peer practices).

- getWeather(lat, lng, date)
  → Use only for weather-sensitive businesses or clearly outdoor, in-person events to set event weather_badge (good|mixed|poor) based on forecast. (Note: If tool not available, leave badge null).

🧩 INPUTS

- User Query: "{query}"
- Business Profile: {json.dumps(scope, default=str)}
- Opportunities Profile: {json.dumps(opportunities_profile, default=str) if opportunities_profile else "None"}

(Note: Profiles are already provided above, no need to fetch).

🌐 WEB RESEARCH & BENCHMARKS

Use search_web to:

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

Populate:
- benchmarks[] with simple numeric or directional benchmarks.
- digest.opportunities and advisor.actions with “what top performers are doing that this business could emulate.”

🧱 OUTPUT FORMAT — STRICT JSON ONLY

Return one object shaped as:

{{
  "query": "original user text",
  "scope": {{
    "company_id": "demo|{{id}}",
    "industry": "string",
    "naics": "string|null",
    "location": {{"city":"", "state":"", "lat":0, "lng":0}},
    "radius_miles": 50,
    "window_days": 14,
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

⚙️ BEHAVIOR RULES

- Use search_web for:
  • opportunities (events, RFPs, grants, partnerships, listings, training), and
  • benchmarks & peer practices.
- Vary sources by type (event platforms, city calendars, SAM.gov/grants.gov/state portals, trade associations, marketplaces, vendor/franchise listings, certification/training registries, industry reports).
- Always include 3–8 sources with valid titles + URLs + dates.
- If nothing is found, return empty cards with an advisor that explains why and suggests new filters (change dates/types/radius, try different channels).
- No fabrication. If an estimate leverages assumptions, include them under ops_plan.assumptions and keep the note short.
- JSON only (no Markdown, no prose outside fields). Keep it concise and owner-friendly.

🧪 DEMO vs LIVE

- mode=demo: you may use conservative ranges and generic providers but still return real, current examples when possible. Mark assumptions clearly.
- mode=live: strictly current items only; prefer official portals/providers.

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
            tool_choice="auto",
            response_format={"type": "json_object"}
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # Handle tool calls loop
        if tool_calls:
            messages.append(response_message)
            
            # Import web_search here to avoid circular import
            from app.routes.ai_opportunities import web_search
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "search_web":
                    search_term = function_args.get("query")
                    recency = function_args.get("recency_days", 30)
                    max_results = function_args.get("max_results", 10)
                    
                    # Execute search
                    search_results = await web_search(search_term, recency, max_results)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(search_results)
                    })
                
                elif function_name == "getWeather":
                    lat = function_args.get("lat")
                    lng = function_args.get("lng")
                    date = function_args.get("date")
                    
                    # Execute weather check
                    weather_badge = await self._get_weather_badge({"lat": lat, "lng": lng}, date)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"weather_badge": weather_badge})
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
            print("Failed to parse OpenAI JSON response")
            raise ValueError("Invalid JSON response from OpenAI")

    async def _get_weather_badge(
        self,
        location: Dict[str, Any],
        date: Optional[str] = None,
    ) -> Optional[str]:
        """
        getWeather(lat, lng, date) tool - Get weather badge for events.
        Returns: "good" | "mixed" | "poor" | None
        
        Exact logic from agent prompt:
        - good: precip <20%, wind <15 mph, temp 55-85°F
        - mixed: precip <50% or wind 15-25 mph
        - poor: else
        """
        if not location.get("lat") or not location.get("lng"):
            return None
        
        try:
            import os
            import httpx
            
            weather_api_key = os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHERAPI_KEY")
            if weather_api_key:
                # Call weather API
                lat = location.get("lat")
                lng = location.get("lng")
                
                # Try OpenWeatherMap first
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        url = "https://api.openweathermap.org/data/2.5/forecast"
                        params = {
                            "lat": lat,
                            "lon": lng,
                            "appid": weather_api_key,
                            "units": "imperial",  # For Fahrenheit
                        }
                        response = await client.get(url, params=params)
                        if response.status_code == 200:
                            data = response.json()
                            forecast = data.get("list", [{}])[0]
                            main = forecast.get("main", {})
                            weather = forecast.get("weather", [{}])[0]
                            wind = forecast.get("wind", {})
                            
                            temp = main.get("temp", 70)
                            wind_speed = wind.get("speed", 5)
                            pop = forecast.get("pop", 0) * 100
                            
                            if pop < 20 and wind_speed < 15 and 55 <= temp <= 85:
                                return "good"
                            elif pop < 50 or (15 <= wind_speed <= 25):
                                return "mixed"
                            else:
                                return "poor"
                except Exception as e:
                    print(f"Weather API error: {e}")
                    pass
            
            return None
        except Exception:
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

🧰 TOOLS

- search_web(query, recency_days, max_results)
  → Use to find real-world data: equipment prices, interest rates, labor rates, market benchmarks.

📊 INPUTS

- **Scenario Type**: {scenario_type}
- **User Query**: "{query}"
- **Industry**: {industry}
- **Business Profile**: {json.dumps(business_profile, default=str) if business_profile else "None"}

🎯 OUTPUT FORMAT — STRICT JSON ONLY

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

⚙️ BEHAVIOR RULES

- **CRITICAL**: DO NOT USE 'example.com' or 'test.com'. If you cannot find a source, leave the source field null or omit the assumption.
- Use search_web to find real data for ALL assumptions.
- Common assumptions by scenario type:
  - **CapEx**: equipment_cost, financing_rate, useful_life_years, maintenance_cost_annual
  - **Hiring**: salary_annual, benefits_cost_pct, training_cost, productivity_ramp_months
  - **Pricing**: competitor_prices, price_elasticity, market_avg_price
  - **Expansion**: location_rent, build_out_cost, time_to_revenue_months
- Always include sources with valid URLs.
- Confidence should reflect data quality (0.0-1.0).
- If data is not available, use industry averages and note the assumption.

✅ QUALITY CHECK BEFORE RETURN

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
                    "name": "search_web",
                    "description": "Search the web for real-time information about prices, rates, and market data.",
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
            
            # Import web_search here to avoid circular import
            from app.routes.ai_opportunities import web_search
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "search_web":
                    search_term = function_args.get("query")
                    recency = function_args.get("recency_days", 30)
                    max_results = function_args.get("max_results", 10)
                    
                    # Execute search
                    search_results = await web_search(search_term, recency, max_results)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(search_results)
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
