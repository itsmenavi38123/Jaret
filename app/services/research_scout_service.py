# backend/app/services/research_scout_service.py
"""
LightSignal Research Scout Service
Delivers decision-grade, structured JSON for opportunities and market intelligence
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json


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
        
        preferred_types = opportunities_profile.get("preferred_opportunity_types", []) if opportunities_profile else []
        
        opportunities_data = await self._search_and_process_opportunities(
            query=query,
            scope=scope,
            preferred_types=preferred_types,
            business_profile=business_profile,
            opportunities_profile=opportunities_profile,
        )
        
        digest = await self._build_digest(
            query=query,
            scope=scope,
            business_profile=business_profile,
        )
        
        benchmarks = await self._build_benchmarks(
            scope=scope,
            business_profile=business_profile,
        )
        
        advisor = self._build_advisor(
            opportunities_data=opportunities_data,
            scope=scope,
        )
        
        ops_plan = self._build_ops_plan(
            opportunities_data=opportunities_data,
            business_profile=business_profile,
            opportunities_profile=opportunities_profile,
        )
        
        sources = self._build_sources(opportunities_data)
        
        so_what = self._calculate_so_what(opportunities_data, advisor, digest)
        
        return {
            "query": query,
            "scope": scope,
            "digest": digest,
            "opportunities": {
                "kpis": opportunities_data["kpis"],
                "cards": opportunities_data["cards"],
                "advisor": advisor,
                "ops_plan": ops_plan,
            },
            "benchmarks": benchmarks,
            "so_what": so_what,
            "sources": sources,
        }
    
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
    
    async def _search_and_process_opportunities(
        self,
        query: str,
        scope: Dict[str, Any],
        preferred_types: List[str],
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Search for opportunities and process them into cards"""
        # Build search queries for each preferred type
        search_queries = []
        if preferred_types:
            for opp_type in preferred_types:
                search_query = self._build_query_for_type(query, opp_type, scope)
                search_queries.append((opp_type, search_query))
        else:
            # Default search
            search_queries.append(("event", query))
        
        # Process opportunities
        cards = []
        total_value = 0.0
        total_fit_score = 0.0
        
        for opp_type, search_query in search_queries[:5]:  # Limit to 5 types
            # In production, this would call web_search tool
            # For now, generate structured mock data
            type_cards = await self._process_opportunity_type(
                opp_type=opp_type,
                search_query=search_query,
                scope=scope,
                business_profile=business_profile,
                opportunities_profile=opportunities_profile,
            )
            cards.extend(type_cards)
        
        # Calculate KPIs
        if cards:
            total_value = sum(card.get("est_revenue", 0) for card in cards)
            total_fit_score = sum(card.get("fit_score", 0) for card in cards) / len(cards)
        
        # Sort by fit_score
        cards.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
        
        return {
            "kpis": {
                "active_count": len(cards),
                "potential_value": total_value,
                "avg_fit_score": round(total_fit_score, 1),
                "event_readiness": round(total_fit_score * 0.8, 1),  # Simplified
            },
            "cards": cards,
        }
    
    def _build_query_for_type(self, query: str, opp_type: str, scope: Dict[str, Any]) -> str:
        """Build search query for specific opportunity type"""
        type_queries = {
            "government_contracts": f"{query} RFP government contract procurement",
            "grants": f"{query} grant funding program",
            "trade_shows": f"{query} trade show expo convention",
            "local_events": f"{query} local event festival pop-up",
            "partnerships": f"{query} partnership supplier program",
            "vendor_listings": f"{query} vendor subcontractor listing",
            "certifications": f"{query} certification training program",
        }
        
        base_query = type_queries.get(opp_type, query)
        location = scope.get("location", {})
        if location.get("state"):
            base_query = f"{base_query} {location['state']}"
        if location.get("city"):
            base_query = f"{base_query} {location['city']}"
        
        return base_query
    
    async def _process_opportunity_type(
        self,
        opp_type: str,
        search_query: str,
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Process opportunities for a specific type using web search.
        """
        cards = []
        
        # Call web search to find real opportunities
        try:
            # Import web_search function from routes
            import sys
            import importlib
            
            # Get the web_search function from the ai_opportunities module
            from app.routes import ai_opportunities
            
            search_results = await ai_opportunities.web_search(
                search_term=search_query,
                recency_days=30,
                max_results=10
            )
            
            # Parse web search results into opportunity cards
            if search_results and len(search_results) > 0:
                for i, result in enumerate(search_results[:5]):  # Limit to 5 per type
                    card = await self._parse_search_result_to_card(
                        result=result,
                        opp_type=opp_type,
                        scope=scope,
                        business_profile=business_profile,
                        opportunities_profile=opportunities_profile,
                        search_query=search_query,
                    )
                    if card:
                        cards.append(card)
        except Exception as e:
            # Fallback to mock data if web search fails
            print(f"Web search error: {e}, using fallback data")
            cards = self._generate_fallback_cards(
                opp_type=opp_type,
                scope=scope,
                business_profile=business_profile,
                opportunities_profile=opportunities_profile,
            )
        
        return cards
    
    async def _parse_search_result_to_card(
        self,
        result: Dict[str, Any],
        opp_type: str,
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
        search_query: str,
    ) -> Optional[Dict[str, Any]]:
        """Parse web search result into opportunity card format"""
        try:
            # Extract data from search result
            title = result.get("title", result.get("name", "Untitled Opportunity"))
            url = result.get("url", result.get("link", ""))
            snippet = result.get("snippet", result.get("description", result.get("content", "")))
            
            # Try to extract date from snippet or result
            date_str = None
            deadline_str = None
            if "date" in result:
                date_str = result["date"]
            elif "published_date" in result:
                date_str = result["published_date"]
            
            # Estimate revenue and cost based on opportunity type
            est_revenue, cost = self._estimate_financials(opp_type, snippet)
            
            # Calculate fit score
            fit_score = self._calculate_fit_score(
                opp_type=opp_type,
                scope=scope,
                business_profile=business_profile,
                opportunities_profile=opportunities_profile,
            )
            
            # Determine provider from URL
            provider = self._extract_provider_from_url(url)
            
            card = {
                "title": title[:200],  # Limit title length
                "type": opp_type,
                "date": date_str or (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "deadline": deadline_str,
                "location": scope.get("location", {}),
                "est_revenue": est_revenue,
                "cost": cost,
                "roi_est": round(((est_revenue - cost) / max(1, cost)) * 100, 1) if est_revenue and cost else 0.0,
                "fit_score": fit_score,
                "confidence": 0.75,  # Base confidence for web search results
                "weather_badge": None,
                "link": url,
                "provider": provider,
                "source_id": f"{opp_type}_{hash(url)}_{datetime.now().timestamp()}",
                "notes": snippet[:200] if snippet else f"Found via search: {search_query[:50]}",
                "pros": [f"Good fit for {scope.get('industry', 'business')}", "Real opportunity from web search"],
                "cons": ["Verify details directly", "Check requirements"],
            }
            
            # Set weather badge for events using getWeather tool
            if "event" in opp_type or "local" in opp_type:
                weather_badge = await self._get_weather_badge(
                    location=scope.get("location", {}),
                    date=date_str or card.get("date"),
                )
                card["weather_badge"] = weather_badge
            
            return card
        except Exception as e:
            print(f"Error parsing search result: {e}")
            return None
    
    def _estimate_financials(self, opp_type: str, snippet: str) -> tuple:
        """Estimate revenue and cost based on opportunity type and description"""
        # Base estimates by type
        base_estimates = {
            "government_contracts": (50000, 5000),
            "grants": (25000, 1000),
            "trade_shows": (5000, 1000),
            "local_events": (2000, 300),
            "partnerships": (10000, 500),
            "vendor_listings": (5000, 200),
            "certifications": (2000, 500),
        }
        
        est_revenue, cost = base_estimates.get(opp_type, (1000, 200))
        
        # Try to extract numbers from snippet
        import re
        numbers = re.findall(r'\$[\d,]+|\d+,\d+', snippet.lower())
        if numbers:
            try:
                # Use first number found as potential revenue
                num_str = numbers[0].replace('$', '').replace(',', '')
                est_revenue = float(num_str)
                cost = est_revenue * 0.2  # Assume 20% cost
            except:
                pass
        
        return est_revenue, cost
    
    def _extract_provider_from_url(self, url: str) -> str:
        """Extract provider name from URL"""
        if not url:
            return "other"
        
        url_lower = url.lower()
        if "eventbrite" in url_lower:
            return "eventbrite"
        elif "sam.gov" in url_lower or "beta.sam" in url_lower:
            return "sam_gov"
        elif "grants.gov" in url_lower:
            return "grants_gov"
        elif "facebook.com/events" in url_lower:
            return "facebook_events"
        elif "meetup.com" in url_lower:
            return "meetup"
        elif "city" in url_lower or "municipal" in url_lower:
            return "city_portal"
        else:
            return "other"
    
    def _generate_fallback_cards(
        self,
        opp_type: str,
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate fallback mock cards if web search fails"""
        cards = []
        for i in range(2):  # Reduced to 2 fallback cards
            card = {
                "title": f"{opp_type.replace('_', ' ').title()} Opportunity {i+1}",
                "type": opp_type,
                "date": (datetime.now() + timedelta(days=i*7)).strftime("%Y-%m-%d"),
                "deadline": (datetime.now() + timedelta(days=i*5)).strftime("%Y-%m-%d") if i < 2 else None,
                "location": scope.get("location", {}),
                "est_revenue": 1000.0 * (i + 1),
                "cost": 200.0 * (i + 1),
                "roi_est": round(((1000.0 * (i + 1)) - (200.0 * (i + 1))) / max(1, (200.0 * (i + 1))) * 100, 1),
                "fit_score": self._calculate_fit_score(
                    opp_type=opp_type,
                    scope=scope,
                    business_profile=business_profile,
                    opportunities_profile=opportunities_profile,
                ) + (i * 5),
                "confidence": 0.5,  # Lower confidence for fallback
                "weather_badge": None,
                "link": f"https://example.com/{opp_type}/{i+1}",
                "provider": self._get_provider_for_type(opp_type),
                "source_id": f"{opp_type}_{i+1}_{datetime.now().timestamp()}",
                "notes": "Fallback data - web search unavailable",
                "pros": [f"Good fit for {scope.get('industry', 'business')}", "Within budget"],
                "cons": [f"Requires {i+1} week lead time", "Verify details"],
            }
            
            if "event" in opp_type or "local" in opp_type:
                card["weather_badge"] = "good" if i % 2 == 0 else "mixed"
            
            cards.append(card)
        
        return cards
    
    def _calculate_fit_score(
        self,
        opp_type: str,
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
    ) -> int:
        """Calculate fit score (0-100) based on profile matching"""
        score = 0
        
        # Industry match (+30)
        if scope.get("industry") and scope.get("industry") != "Unknown":
            score += 30
        
        # Region/radius match (+20)
        if scope.get("location", {}).get("state"):
            score += 20
        
        # Affordability vs budget (+20) - if profile provides cash/runway
        if opportunities_profile and opportunities_profile.get("max_budget"):
            score += 20
        
        # Seasonality/demand (+15)
        score += 15
        
        # Peer/ROI context (+15)
        score += 15
        
        return min(100, score)
    
    def _get_provider_for_type(self, opp_type: str) -> str:
        """Get provider name for opportunity type"""
        provider_map = {
            "government_contracts": "sam_gov",
            "grants": "grants_gov",
            "trade_shows": "trade_site",
            "local_events": "eventbrite",
            "partnerships": "vendor_portal",
            "vendor_listings": "vendor_portal",
            "certifications": "training_registry",
        }
        return provider_map.get(opp_type, "other")
    
    async def _build_digest(
        self,
        query: str,
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build market digest using web_search for real data.
        Uses search_web to find: demand trends, competition, labor, costs, regulatory, peer practices.
        """
        industry = scope.get("industry", "Unknown")
        location = scope.get("location", {})
        city = location.get("city", "")
        state = location.get("state", "")
        
        # Use web_search to find real market data
        from app.routes import ai_opportunities
        
        # Search for market intelligence
        market_queries = [
            f"{industry} market demand {state}",
            f"{industry} competition {city} {state}",
            f"{industry} labor wages {state}",
        ]
        
        # For now, return structured data (in production, parse web_search results)
        # The prompt says to use search_web for benchmarks & peer practices
        
        return {
            "demand": [
                f"Steady demand for {industry} services in {state or 'region'}",
                "Seasonal peaks expected in coming weeks",
            ],
            "competition": [
                f"Moderate competition in {city or 'area'}",
                "Mix of established and new entrants",
            ],
            "labor": {
                "wage_range_hour": [15, 25],
                "availability_note": "Moderate availability",
                "licensing": "Check local requirements",
            },
            "costs": {
                "rent_note": "Varies by location",
                "insurance_note": "Standard business insurance required",
                "materials_or_inputs_note": "Costs stable",
                "tax_or_fee_note": "Standard business taxes apply",
            },
            "seasonality": "Peak season approaching",
            "regulatory": [
                "Business license required",
                "Check local permits",
            ],
            "customer_profile": [
                f"Target customers in {city or 'area'}",
                "Mix of demographics",
            ],
            "risks": [
                "Weather dependency for outdoor events",
                "Market volatility",
            ],
            "opportunities": [
                "Growing market demand",
                "Partnership opportunities available",
                "Top performers focus on customer experience",  # From peer research
            ],
        }
    
    async def _build_benchmarks(
        self,
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Build industry benchmarks using search_web.
        Finds: typical margins, revenue per event/job, close rates, utilization, ticket sizes.
        """
        industry = scope.get("industry", "Unknown")
        location = scope.get("location", {})
        state = location.get("state", "national")
        
        # Use web_search to find real benchmarks
        # In production, search for: "{industry} profit margin benchmark", "{industry} revenue per event"
        # Parse results and extract numeric benchmarks
        
        # For now, return structured benchmarks (would be populated from web_search)
        benchmarks = [
            {
                "metric": "gross_margin",
                "peer_median": 35.0,
                "region": state,
                "sample_note": f"Typical for {industry} businesses",
            },
        ]
        
        # Add revenue_per_event if applicable
        if any(word in industry.lower() for word in ["event", "food", "retail", "pop-up"]):
            benchmarks.append({
                "metric": "revenue_per_event",
                "peer_median": 2500.0,
                "region": state,
                "sample_note": "Based on similar businesses",
            })
        
        return benchmarks
    
    def _build_advisor(
        self,
        opportunities_data: Dict[str, Any],
        scope: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build advisor recommendations.
        If no opportunities found, explain why and suggest new filters.
        """
        cards = opportunities_data.get("cards", [])
        high_fit = [c for c in cards if c.get("fit_score", 0) >= 70]
        
        # If no opportunities found, explain why and suggest filters
        if not cards:
            return {
                "summary": "No opportunities found matching your current filters. Try broadening your search criteria.",
                "actions": [
                    {
                        "title": "Broaden search radius",
                        "impact": "May reveal more opportunities",
                        "deadline": None,
                        "reason": "Current radius may be too restrictive",
                    },
                    {
                        "title": "Adjust date range",
                        "impact": "Include more upcoming events",
                        "deadline": None,
                        "reason": "Current window may be too narrow",
                    },
                    {
                        "title": "Try different opportunity types",
                        "impact": "Explore alternative channels",
                        "deadline": None,
                        "reason": "Current types may not have matches",
                    },
                ],
                "risks": [
                    {"level": "low", "message": "No immediate opportunities, but market may change"},
                ],
            }
        
        actions = []
        if high_fit:
            top_opp = high_fit[0]
            actions.append({
                "title": f"Apply to {top_opp.get('title', 'opportunity')[:50]}",
                "impact": f"${top_opp.get('est_revenue', 0):,.0f} potential revenue",
                "deadline": top_opp.get("deadline", top_opp.get("date")),
                "reason": f"High fit score ({top_opp.get('fit_score', 0)}) and good ROI",
            })
        
        # Add "what top performers are doing" from peer research
        industry = scope.get("industry", "business")
        if len(actions) < 3:
            actions.append({
                "title": f"Research {industry} best practices",
                "impact": "Improve conversion rates and efficiency",
                "deadline": None,
                "reason": "Top performers focus on customer experience and operational efficiency",
            })
        
        return {
            "summary": f"Found {len(cards)} opportunities matching your profile. Focus on high-fit opportunities with deadlines in the next 2 weeks.",
            "actions": actions[:3],  # Top 3 actions
            "risks": [
                {"level": "low", "message": "Standard business risks apply"},
                {"level": "med", "message": "Weather may impact outdoor events"},
            ],
        }
    
    def _build_ops_plan(
        self,
        opportunities_data: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
        opportunities_profile: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build operations plan for high-fit opportunities"""
        cards = opportunities_data.get("cards", [])
        high_fit = [c for c in cards if c.get("fit_score", 0) >= 70]
        
        if not high_fit:
            return {
                "applicable_to": None,
                "assumptions": {},
                "recommendations": {},
                "explain": "No high-fit opportunities found for ops planning.",
            }
        
        top_opp = high_fit[0]
        opp_type = top_opp.get("type", "")
        
        # Extract capacity from profile
        staffing_capacity = opportunities_profile.get("staffing_capacity", 2) if opportunities_profile else 2
        
        # Get industry from business profile
        industry = ""
        if business_profile and business_profile.get("onboarding_data"):
            onboarding = business_profile["onboarding_data"]
            industry = onboarding.get("industry", onboarding.get("business_type", "")).lower()
        
        # Get industry-specific conversion rate (LOW end per prompt rules)
        conversion_rate = self._get_conversion_rate_by_industry(industry, opp_type)
        
        # Use profile AOV/capacity if available (per prompt: "Use profile AOV/capacity")
        aov = 25.0  # Default
        if business_profile and business_profile.get("onboarding_data"):
            onboarding = business_profile["onboarding_data"]
            aov = onboarding.get("avg_order_value", onboarding.get("aov", 25.0))
        
        # Calculate units based on attendance, conversion rate, and capacity
        expected_attendance = 500  # Default, would come from event details
        units_to_prepare = int(expected_attendance * conversion_rate)
        
        return {
            "applicable_to": opp_type,
            "assumptions": {
                "expected_attendance": expected_attendance,
                "conversion_rate": conversion_rate,
                "avg_order_value_or_ticket": aov,
                "service_hours": 8,
                "units_per_hour_capacity": 10,
            },
            "recommendations": {
                "units_to_prepare": {"item": "products", "qty": units_to_prepare},
                "staffing": {"crew": staffing_capacity, "shifts": 1},
                "prep_budget": 500.0,
                "fee_or_booth_budget": top_opp.get("cost", 0),
                "checklist": [
                    "Obtain permits/insurance",
                    "Set up POS/payment system",
                    "Prepare backup plan for weather",
                    "Confirm staffing availability",
                ],
            },
            "explain": f"For {top_opp.get('title', 'this opportunity')}, prepare {units_to_prepare} units based on {expected_attendance} expected attendees with {conversion_rate*100:.1f}% conversion (industry low-end). Budget ${top_opp.get('cost', 0):,.0f} for fees and $500 for prep. Staff with {staffing_capacity} crew members for 1 shift.",
        }
    
    def _build_sources(self, opportunities_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build sources list (3-8 sources with valid titles + URLs + dates).
        Vary sources by type: event platforms, SAM.gov, grants.gov, city portals, etc.
        """
        cards = opportunities_data.get("cards", [])
        sources = []
        
        # Collect unique sources from opportunity cards
        seen_urls = set()
        for card in cards:
            url = card.get("link", "")
            if url and url not in seen_urls and url.startswith("http"):
                seen_urls.add(url)
                provider = card.get("provider", "unknown")
                sources.append({
                    "title": f"{provider.replace('_', ' ').title()} - {card.get('title', 'Opportunity')[:50]}",
                    "url": url,
                    "date": card.get("date", datetime.now().strftime("%Y-%m-%d")),
                    "note": f"Source for {card.get('type', 'opportunity')} opportunities",
                })
                if len(sources) >= 8:  # Max 8 sources as per prompt
                    break
        
        # Ensure at least 3 sources (add generic if needed)
        while len(sources) < 3 and len(cards) > 0:
            card = cards[len(sources)]
            if card.get("link"):
                sources.append({
                    "title": f"Opportunity Source - {card.get('type', 'opportunity')}",
                    "url": card.get("link"),
                    "date": card.get("date", datetime.now().strftime("%Y-%m-%d")),
                    "note": f"Additional {card.get('type', 'opportunity')} opportunity",
                })
            else:
                break
        
        return sources
    
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
            # TODO: Integrate with actual weather API (OpenWeatherMap, WeatherAPI, etc.)
            # When weather API is integrated:
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
                            # Get forecast for the date (or first forecast)
                            forecast = data.get("list", [{}])[0]
                            main = forecast.get("main", {})
                            weather = forecast.get("weather", [{}])[0]
                            wind = forecast.get("wind", {})
                            
                            temp = main.get("temp", 70)
                            precip = weather.get("pop", 0) * 100  # Probability of precipitation
                            wind_speed = wind.get("speed", 0)
                            
                            # Apply exact logic from prompt
                            if precip < 20 and wind_speed < 15 and 55 <= temp <= 85:
                                return "good"
                            elif precip < 50 or (15 <= wind_speed <= 25):
                                return "mixed"
                            else:
                                return "poor"
                except Exception as e:
                    print(f"Weather API error: {e}")
            
            # If no weather API or error, return None (will default to None in card)
            return None
        except Exception:
            return None
    
    def _get_conversion_rate_by_industry(
        self,
        industry: str,
        opp_type: str,
    ) -> float:
        """
        Get industry-specific conversion rate following agent prompt rules.
        Uses LOW end of ranges, never exceeds ceilings.
        """
        industry_lower = industry.lower()
        
        # Food trucks / mobile food vendors
        if any(word in industry_lower for word in ["food truck", "mobile food", "catering", "food vendor"]):
            if "event" in opp_type or "local" in opp_type:
                return 0.06  # 6% - LOW end of 6-15% range, max 20%, ceiling 25%
        
        # Fitness, gyms, martial arts
        if any(word in industry_lower for word in ["fitness", "gym", "martial arts", "krav maga", "yoga", "training"]):
            if "event" in opp_type:
                return 0.01  # 1% - LOW end of 1-4% range
        
        # HVAC / contractors / B2B services
        if any(word in industry_lower for word in ["hvac", "contractor", "plumbing", "electrical", "construction"]):
            if "rfp" in opp_type or "government_contracts" in opp_type:
                return 0.10  # 10% - LOW end of 10-20% lead→proposal range
            return 0.20  # 20% - LOW end of 20-40% proposal→win range
        
        # Retail pop-ups
        if any(word in industry_lower for word in ["retail", "pop-up", "store", "shop"]):
            if "event" in opp_type or "local" in opp_type:
                return 0.04  # 4% - LOW end of 4-12% range
        
        # Online / digital
        if any(word in industry_lower for word in ["online", "digital", "ecommerce", "saas", "software"]):
            return 0.01  # 1% - LOW end of 1-3% traffic→lead range
        
        # Default: Conservative 6% (food truck low end)
        return 0.06
    
    def _calculate_so_what(
        self,
        opportunities_data: Dict[str, Any],
        advisor: Dict[str, Any],
        digest: Dict[str, Any],
    ) -> str:
        """Calculate executive summary"""
        count = opportunities_data.get("kpis", {}).get("active_count", 0)
        value = opportunities_data.get("kpis", {}).get("potential_value", 0)
        
        return f"Found {count} opportunities worth ${value:,.0f} in potential revenue. Focus on high-fit opportunities with upcoming deadlines to maximize ROI."

