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
        
        TODO: Integrate web_search tool here:
        1. Call web_search(search_query, recency_days=30, max_results=10)
        2. Parse results and extract: title, description, date, location, URL
        3. Map to opportunity cards with fit scoring
        4. For events, call getWeather() to set weather_badge
        """
        
        cards = []
        
        # In production, this would call:
        # web_search_results = await web_search(search_query, recency_days=30, max_results=10)
        # Then parse and structure the results
        
        # For now, generate structured mock data that matches the format
        for i in range(3):  # 3 opportunities per type
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
                "confidence": 0.7 + (i * 0.1),
                "weather_badge": None,
                "link": f"https://example.com/{opp_type}/{i+1}",
                "provider": self._get_provider_for_type(opp_type),
                "source_id": f"{opp_type}_{i+1}_{datetime.now().timestamp()}",
                "notes": f"Found via search: {search_query[:50]}",
                "pros": [f"Good fit for {scope.get('industry', 'business')}", "Within budget"],
                "cons": [f"Requires {i+1} week lead time", "Weather dependent"],
            }
            
            # Set weather badge for events
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
        """Build market digest"""
        industry = scope.get("industry", "Unknown")
        
        return {
            "demand": [
                f"Steady demand for {industry} services in {scope.get('location', {}).get('state', 'region')}",
                "Seasonal peaks expected in coming weeks",
            ],
            "competition": [
                f"Moderate competition in {scope.get('location', {}).get('city', 'area')}",
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
                f"Target customers in {scope.get('location', {}).get('city', 'area')}",
                "Mix of demographics",
            ],
            "risks": [
                "Weather dependency for outdoor events",
                "Market volatility",
            ],
            "opportunities": [
                "Growing market demand",
                "Partnership opportunities available",
                "Top performers focus on customer experience",
            ],
        }
    
    async def _build_benchmarks(
        self,
        scope: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build industry benchmarks"""
        industry = scope.get("industry", "Unknown")
        location = scope.get("location", {})
        
        return [
            {
                "metric": "gross_margin",
                "peer_median": 35.0,
                "region": location.get("state", "national"),
                "sample_note": f"Typical for {industry} businesses",
            },
            {
                "metric": "revenue_per_event",
                "peer_median": 2500.0,
                "region": location.get("state", "national"),
                "sample_note": "Based on similar businesses",
            },
        ]
    
    def _build_advisor(
        self,
        opportunities_data: Dict[str, Any],
        scope: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build advisor recommendations"""
        cards = opportunities_data.get("cards", [])
        high_fit = [c for c in cards if c.get("fit_score", 0) >= 70]
        
        actions = []
        if high_fit:
            top_opp = high_fit[0]
            actions.append({
                "title": f"Apply to {top_opp.get('title', 'opportunity')}",
                "impact": f"${top_opp.get('est_revenue', 0):,.0f} potential revenue",
                "deadline": top_opp.get("deadline", top_opp.get("date")),
                "reason": f"High fit score ({top_opp.get('fit_score', 0)}) and good ROI",
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
        
        return {
            "applicable_to": opp_type,
            "assumptions": {
                "expected_attendance": 500,
                "conversion_rate": 0.10,  # 10% conservative
                "avg_order_value_or_ticket": 25.0,
                "service_hours": 8,
                "units_per_hour_capacity": 10,
            },
            "recommendations": {
                "units_to_prepare": {"item": "products", "qty": 80},
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
            "explain": f"For {top_opp.get('title', 'this opportunity')}, prepare 80 units based on 500 expected attendees with 10% conversion. Budget ${top_opp.get('cost', 0):,.0f} for fees and $500 for prep. Staff with {staffing_capacity} crew members for 1 shift.",
        }
    
    def _build_sources(self, opportunities_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build sources list"""
        cards = opportunities_data.get("cards", [])
        sources = []
        
        providers = set()
        for card in cards[:5]:
            provider = card.get("provider", "unknown")
            if provider not in providers:
                providers.add(provider)
                sources.append({
                    "title": f"{provider.replace('_', ' ').title()} Listing",
                    "url": card.get("link", ""),
                    "date": card.get("date", datetime.now().strftime("%Y-%m-%d")),
                    "note": f"Source for {card.get('type', 'opportunity')} opportunities",
                })
        
        return sources
    
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

