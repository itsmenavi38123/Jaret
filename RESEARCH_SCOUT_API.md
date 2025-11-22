# LightSignal Research Scout API Documentation

## Overview

The Research Scout API is an intelligence service that delivers decision-grade, structured JSON combining:
- Current market/region digest
- Personalized opportunity feed (events, RFPs, grants, partnerships, listings)
- Fit scoring, weather badges, ROI estimates
- Advisor recommendations
- Operations planning
- Industry benchmarks

**Key Principle**: Every claim is grounded in real data from web search. No fabricated events, RFPs, or benchmarks.

---

## Architecture & Flow

### High-Level Flow

```
User Request
    ↓
1. Authenticate (JWT token)
    ↓
2. Fetch User Profiles
    ├── Business Profile (industry, NAICS, region)
    └── Opportunities Profile (preferred types, radius, budget, capacity)
    ↓
3. Research Scout Service
    ├── Build Scope (company_id, industry, location, types, mode)
    ├── Search Opportunities (web_search for each preferred type)
    ├── Build Market Digest (demand, competition, labor, costs)
    ├── Build Benchmarks (industry peer metrics)
    ├── Calculate Fit Scores (0-100 based on profile matching)
    ├── Get Weather Badges (for events, using getWeather)
    ├── Build Advisor (recommendations, actions, risks)
    └── Build Ops Plan (for high-fit opportunities)
    ↓
4. Return Structured JSON
```

### Component Structure

```
app/
├── routes/
│   └── ai_opportunities.py          # API endpoints
│       ├── POST /api/ai/opportunities/search
│       ├── GET /api/ai/opportunities/search
│       └── web_search()             # Web search helper
│
└── services/
    └── research_scout_service.py     # Core business logic
        ├── search_opportunities()    # Main entry point
        ├── _build_scope()            # Build scope object
        ├── _search_and_process_opportunities()  # Find & parse opportunities
        ├── _process_opportunity_type()          # Process each type
        ├── _parse_search_result_to_card()       # Convert search → card
        ├── _calculate_fit_score()               # Score 0-100
        ├── _get_weather_badge()                 # Weather API integration
        ├── _get_conversion_rate_by_industry()   # Industry-specific rates
        ├── _build_digest()                      # Market intelligence
        ├── _build_benchmarks()                  # Peer metrics
        ├── _build_advisor()                     # Recommendations
        ├── _build_ops_plan()                    # Operations planning
        ├── _build_sources()                     # Source citations
        └── _calculate_so_what()                 # Executive summary
```

---

## API Endpoints

### POST `/api/ai/opportunities/search`

Search for opportunities using Research Scout.

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `mode` (optional): `"demo"` or `"live"` (default: `"live"`)

**Request Body**:
```json
{
  "query": "What can a food truck do this weekend near Tampa?",
  "opportunity_types": ["local_events", "trade_shows"],  // Optional
  "limit": 10  // Optional, default: 10
}
```

**Response**: Strict JSON matching Research Scout format (see Response Format below)

---

### GET `/api/ai/opportunities/search`

GET version of search endpoint.

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `query` (required): Search query string
- `opportunity_types` (optional): Comma-separated types (e.g., `"local_events,trade_shows"`)
- `limit` (optional): Max results (default: 10)
- `mode` (optional): `"demo"` or `"live"` (default: `"live"`)

**Example**:
```
GET /api/ai/opportunities/search?query=food%20truck%20events&opportunity_types=local_events&limit=10&mode=live
```

---

## Response Format

The API returns strict JSON-only responses with the following structure:

```json
{
  "query": "original user text",
  "scope": {
    "company_id": "user_id_123",
    "industry": "Food Truck",
    "naics": "722320",
    "location": {
      "city": "Tampa",
      "state": "FL",
      "lat": 27.9506,
      "lng": -82.4572
    },
    "radius_miles": 50,
    "window_days": 14,
    "types": ["local_events", "trade_shows"],
    "mode": "live"
  },
  "digest": {
    "demand": ["Steady demand for Food Truck services in FL", "..."],
    "competition": ["Moderate competition in Tampa", "..."],
    "labor": {
      "wage_range_hour": [15, 25],
      "availability_note": "Moderate availability",
      "licensing": "Check local requirements"
    },
    "costs": {
      "rent_note": "Varies by location",
      "insurance_note": "Standard business insurance required",
      "materials_or_inputs_note": "Costs stable",
      "tax_or_fee_note": "Standard business taxes apply"
    },
    "seasonality": "Peak season approaching",
    "regulatory": ["Business license required", "Check local permits"],
    "customer_profile": ["Target customers in Tampa", "..."],
    "risks": ["Weather dependency for outdoor events", "..."],
    "opportunities": ["Growing market demand", "Top performers focus on customer experience"]
  },
  "opportunities": {
    "kpis": {
      "active_count": 5,
      "potential_value": 15000.0,
      "avg_fit_score": 75.5,
      "event_readiness": 60.4
    },
    "cards": [
      {
        "title": "Tampa Food Festival",
        "type": "local_events",
        "date": "2024-12-15",
        "deadline": "2024-12-10",
        "location": {"city": "Tampa", "state": "FL", "lat": 27.9506, "lng": -82.4572},
        "est_revenue": 3000.0,
        "cost": 500.0,
        "roi_est": 500.0,
        "fit_score": 85,
        "confidence": 0.85,
        "weather_badge": "good",
        "link": "https://eventbrite.com/...",
        "provider": "eventbrite",
        "source_id": "local_events_abc123_1234567890",
        "notes": "Found via search: food truck events Tampa",
        "pros": ["Good fit for Food Truck business", "Within budget"],
        "cons": ["Requires 1 week lead time", "Weather dependent"]
      }
    ],
    "advisor": {
      "summary": "Found 5 opportunities matching your profile. Focus on high-fit opportunities with deadlines in the next 2 weeks.",
      "actions": [
        {
          "title": "Apply to Tampa Food Festival",
          "impact": "$3,000 potential revenue",
          "deadline": "2024-12-10",
          "reason": "High fit score (85) and good ROI"
        }
      ],
      "risks": [
        {"level": "low", "message": "Standard business risks apply"},
        {"level": "med", "message": "Weather may impact outdoor events"}
      ]
    },
    "ops_plan": {
      "applicable_to": "local_events",
      "assumptions": {
        "expected_attendance": 500,
        "conversion_rate": 0.06,
        "avg_order_value_or_ticket": 25.0,
        "service_hours": 8,
        "units_per_hour_capacity": 10
      },
      "recommendations": {
        "units_to_prepare": {"item": "products", "qty": 30},
        "staffing": {"crew": 2, "shifts": 1},
        "prep_budget": 500.0,
        "fee_or_booth_budget": 500.0,
        "checklist": [
          "Obtain permits/insurance",
          "Set up POS/payment system",
          "Prepare backup plan for weather",
          "Confirm staffing availability"
        ]
      },
      "explain": "For Tampa Food Festival, prepare 30 units based on 500 expected attendees with 6.0% conversion (industry low-end). Budget $500 for fees and $500 for prep. Staff with 2 crew members for 1 shift."
    }
  },
  "benchmarks": [
    {
      "metric": "gross_margin",
      "peer_median": 35.0,
      "region": "FL",
      "sample_note": "Typical for Food Truck businesses"
    },
    {
      "metric": "revenue_per_event",
      "peer_median": 2500.0,
      "region": "FL",
      "sample_note": "Based on similar businesses"
    }
  ],
  "so_what": "Found 5 opportunities worth $15,000 in potential revenue. Focus on high-fit opportunities with upcoming deadlines to maximize ROI.",
  "sources": [
    {
      "title": "Eventbrite - Tampa Food Festival",
      "url": "https://eventbrite.com/...",
      "date": "2024-12-15",
      "note": "Source for local_events opportunities"
    }
  ]
}
```

---

## Data Flow Details

### 1. Profile Fetching

The service automatically fetches two profiles:

**Business Profile** (`business_profiles` collection):
- Extracts: `industry`, `naics` from `onboarding_data`
- Used for: industry matching, fit scoring, conversion rates

**Opportunities Profile** (`opportunities_profiles` collection):
- Extracts: `preferred_opportunity_types`, `operating_region`, `radius`, `max_budget`, `staffing_capacity`
- Used for: filtering opportunities, calculating fit scores, ops planning

### 2. Web Search Integration

The service uses `web_search()` function which:
1. Tries **Tavily API** first (if `TAVILY_API_KEY` is set)
2. Falls back to **Serper API** (if `SERPER_API_KEY` is set)
3. Falls back to **DuckDuckGo** (no API key needed)

**Search Strategy**:
- For each `preferred_opportunity_types`, builds a search query
- Example: `"food truck local event festival Tampa FL"`
- Searches for: events, RFPs, grants, partnerships, vendor listings, certifications
- Limits to 5 opportunities per type

### 3. Opportunity Processing

For each search result:
1. **Parse** search result → extract title, URL, snippet, date
2. **Calculate fit score** (0-100):
   - Industry match: +30
   - Region/radius match: +20
   - Affordability vs budget: +20
   - Seasonality/demand: +15
   - Peer/ROI context: +15
3. **Estimate financials**: revenue, cost, ROI
4. **Get weather badge** (for events): calls `getWeather()` if location available
5. **Build card** with all required fields

### 4. Fit Score Calculation

```python
fit_score = 0
if industry_match: fit_score += 30
if region_match: fit_score += 20
if budget_affordable: fit_score += 20
fit_score += 15  # seasonality
fit_score += 15  # peer/ROI
return min(100, fit_score)
```

### 5. Weather Badge Logic

For events only, calls `getWeather(lat, lng, date)`:

- **good**: precip <20% AND wind <15 mph AND temp 55-85°F
- **mixed**: precip <50% OR wind 15-25 mph
- **poor**: else
- **null**: if no location or weather API unavailable

### 6. Conversion Rate Rules

Industry-specific conversion rates (using **LOW end** of ranges):

| Industry | Opportunity Type | Conversion Rate |
|----------|-----------------|-----------------|
| Food trucks | Events | 6% (range: 6-15%, max: 20%, ceiling: 25%) |
| Fitness/Gyms | Events | 1% (range: 1-4%) |
| HVAC/Contractors | RFPs | 10% lead→proposal, 20% proposal→win |
| Retail pop-ups | Events | 4% (range: 4-12%) |
| Online/Digital | All | 1% traffic→lead |
| Default | All | 6% (conservative) |

**Important**: Never exceeds industry ceilings. Always uses LOW end when uncertain.

### 7. Ops Plan Generation

Generated only for opportunities with `fit_score >= 70`:

1. **Extract** from profile:
   - `staffing_capacity`
   - `avg_order_value` (AOV) from business profile
2. **Calculate**:
   - `units_to_prepare = expected_attendance × conversion_rate`
   - Uses industry-specific conversion rate (LOW end)
3. **Build** recommendations:
   - Units to prepare
   - Staffing (crew, shifts)
   - Budgets (prep, fees)
   - Checklist

### 8. Advisor Recommendations

**If opportunities found**:
- Top 3 high-fit opportunities
- Actions with impact, deadline, reason
- Risks (low/med/high)

**If no opportunities found**:
- Explains why (filters too restrictive)
- Suggests: broaden radius, adjust dates, try different types

### 9. Sources

- Collects 3-8 unique sources from opportunity cards
- Each source has: title, URL, date, note
- Varies by type: Eventbrite, SAM.gov, Grants.gov, city portals, etc.

---

## Configuration

### Environment Variables

Add to `.env` file:

```ini
# Web Search APIs (optional - will use DuckDuckGo if not set)
TAVILY_API_KEY=your-tavily-api-key
SERPER_API_KEY=your-serper-api-key

# Weather API (optional - for weather badges)
OPENWEATHER_API_KEY=your-openweather-api-key
# OR
WEATHERAPI_KEY=your-weatherapi-key
```

### API Keys Setup

1. **Tavily** (recommended for structured results):
   - Sign up at https://tavily.com
   - Get API key from dashboard
   - Set `TAVILY_API_KEY` in `.env`

2. **Serper** (Google search results):
   - Sign up at https://serper.dev
   - Get API key
   - Set `SERPER_API_KEY` in `.env`

3. **OpenWeatherMap** (for weather badges):
   - Sign up at https://openweathermap.org
   - Get API key
   - Set `OPENWEATHER_API_KEY` in `.env`

---

## Opportunity Types

Supported opportunity types (from `preferred_opportunity_types`):

- `government_contracts` - Government Contracts / RFPs
- `grants` - Grants / Funding Programs
- `trade_shows` - Trade Shows / Industry Expos
- `local_events` - Local Events / Pop-ups / Festivals
- `partnerships` - Partnerships & Supplier Programs
- `vendor_listings` - Vendor or Subcontractor Listings
- `certifications` - Certifications & Training Programs

---

## Error Handling

### No Opportunities Found

If web search returns no results:
- Returns empty `cards` array
- `advisor.summary` explains why
- `advisor.actions` suggests filter changes
- Still returns digest, benchmarks, sources

### Web Search Failure

If all web search APIs fail:
- Falls back to mock data (marked with lower confidence)
- `notes` field indicates "Fallback data - web search unavailable"
- Still returns structured response

### Profile Missing

If user has no profiles:
- Uses query to infer industry/region
- Sets `scope.industry` to "Unknown" if can't infer
- Still processes opportunities with available data

---

## Testing

### Using cURL

**1. Login to get token**:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

**2. Call Research Scout**:
```bash
curl -X POST "http://localhost:8000/api/ai/opportunities/search?mode=live" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "query": "What can a food truck do this weekend near Tampa?",
    "opportunity_types": ["local_events", "trade_shows"],
    "limit": 10
  }'
```

### Using Postman

1. **Method**: POST
2. **URL**: `http://localhost:8000/api/ai/opportunities/search?mode=live`
3. **Headers**:
   - `Authorization: Bearer YOUR_ACCESS_TOKEN`
   - `Content-Type: application/json`
4. **Body** (raw JSON):
```json
{
  "query": "What can a food truck do this weekend near Tampa?",
  "opportunity_types": ["local_events"],
  "limit": 10
}
```

---

## Integration Examples

### Frontend Integration

```javascript
async function searchOpportunities(query, types = []) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('/api/ai/opportunities/search?mode=live', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      opportunity_types: types,
      limit: 10,
    }),
  });
  
  const data = await response.json();
  
  // Use data.opportunities.cards for opportunity list
  // Use data.advisor.actions for recommendations
  // Use data.ops_plan for operations planning
  
  return data;
}
```

### Python Client

```python
import requests

def search_opportunities(query, token, types=None, limit=10):
    url = "http://localhost:8000/api/ai/opportunities/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"mode": "live"}
    data = {
        "query": query,
        "opportunity_types": types or [],
        "limit": limit,
    }
    
    response = requests.post(url, headers=headers, params=params, json=data)
    return response.json()
```

---

## Best Practices

1. **Always set preferred_opportunity_types** in user's opportunities profile
   - Improves fit scores
   - Filters irrelevant opportunities
   - Better user experience

2. **Use mode="demo" for testing**
   - Allows conservative estimates
   - May use generic providers
   - Still returns real examples when possible

3. **Handle empty results gracefully**
   - Check `opportunities.cards.length === 0`
   - Show `advisor.summary` to user
   - Suggest filter changes from `advisor.actions`

4. **Use ops_plan for high-fit opportunities**
   - Only generated for `fit_score >= 70`
   - Includes all assumptions
   - Use for event preparation planning

5. **Monitor confidence scores**
   - Lower confidence = less reliable data
   - May indicate web search issues
   - Consider retrying or using fallback

---

## Troubleshooting

### No opportunities returned

**Check**:
1. User has `opportunities_profile` with `preferred_opportunity_types` set
2. Web search APIs are configured (or DuckDuckGo fallback works)
3. Search queries are not too specific
4. Date range is reasonable (within 14 days default)

**Solution**: Check `advisor.summary` for suggestions

### Weather badges always null

**Check**:
1. Opportunity cards have `location.lat` and `location.lng`
2. Weather API key is set (`OPENWEATHER_API_KEY` or `WEATHERAPI_KEY`)
3. Opportunity type is event-related (`local_events`, `trade_shows`)

**Solution**: Set weather API key or ensure location data in profiles

### Low fit scores

**Check**:
1. Business profile has `industry` set
2. Opportunities profile has `operating_region` and `radius` set
3. Opportunity types match user's `preferred_opportunity_types`

**Solution**: Ensure profiles are complete and accurate

---

## Future Enhancements

- [ ] Tax Research Mode (separate endpoint for tax optimization)
- [ ] Caching of web search results
- [ ] Real-time weather API integration
- [ ] Enhanced benchmark data from multiple sources
- [ ] Historical opportunity tracking
- [ ] Peer ROI comparison database

---

## Support

For questions or issues:
1. Check this documentation
2. Review code comments in `research_scout_service.py`
3. Test with Swagger UI: `http://localhost:8000/docs`
4. Check logs for web search errors

---

**Last Updated**: 2024-12-XX
**Version**: 1.0.0

