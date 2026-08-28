# Live Endpoint Execution Results

**Execution Timestamp:** 2026-08-28T04:25:06.608100 UTC  
**Total Tested Endpoints:** 8  

---

## 1. 1. Scenario Lab Planning (Canonical Scenario Lab v1.4)

- **Status:** `500 FAILED`
- **Method & URL:** `POST /api/ai/scenarios/full`
- **Response Time:** `94.6s`

**Request Body:**
```json
{
  "query": "Hire 2 line cooks at $45k each and expand weekend service hours"
}
```

**Response Summary:**
```json
{
  "error": "Invalid JSON response from Research Scout"
}
```

---

## 2. 2. Dashboard AI Insights (Financial Analyst V6 — INSIGHTS MODE)

- **Status:** `200 PASSED`
- **Method & URL:** `GET /api/ai/insights/latest`
- **Response Time:** `37.39s`

**Response Summary:**
```json
{
  "success": true,
  "data": {
    "summary": "Limited data connected \u2014 cash balance $2,001 but no revenue or expense activity recorded. Connect data sources to enable analysis.",
    "alerts": [
      {
        "severity": "critical",
        "type": "risk",
        "message": "Runway flagged low \u2014 cash balance only $2,001",
        "icon": "\ud83d\udd34"
      },
      {
        "severity": "below_average",
        "type": "warning",
        "message": "No revenue recorded this period",
        "icon": "\ud83d\udfe1"
      },
      {
        "severity": "below_average",
        "type": "warning",
        "message": "No expense data recorded this period",
        "icon": "\ud83d\udfe1"
      },
      {
        "severity": "above_average",
        "type": "positive",
        "message": "Current ratio 1.62 \u2014 short-term obligations covered",
        "icon": "\ud83d\udfe2"
      }
    ],
    "insight_pairs": [
      {
        "problem": "No revenue or expense transactions recorded this period, so runway, margin, and cash flow cannot be calculated \u2014 dashboard reads near-empty because the accounting feed has no activity",
        "solution": "Connect QuickBooks and confirm the transaction sync is active so revenue, expenses, and burn populate for the current period"
      }
    ],
    "opportunities": [],
    "what_changed": [
      "No period-over-period change detected \u2014 both current and prior revenue recorded at $0",
      "Cash balance stands at $2,001 with current ratio 1.62"
    ],
    "missing_data_notice": "Revenue, expenses, and margin all read $0 or null and no classifier profile is present. Connect QuickBooks and complete the Industry & Model section of your profile to enable peer comparison, runway calibration, and full dashboard analysis."
  }
}
```

---

## 3. 3. Financial Overview Drawer Forensics (Financial Analyst V6 — DRAWER MODE)

- **Status:** `200 PASSED`
- **Method & URL:** `POST /api/financial-overview/drawer`
- **Response Time:** `10.67s`

**Request Body:**
```json
{
  "kpi_name": "net_margin_pct",
  "current_value": 0.18,
  "prior_value": 0.14,
  "format_type": "percentage"
}
```

**Response Summary:**
```json
{
  "success": true,
  "data": {
    "kpi_name": "net_margin_pct",
    "headline": "net_margin_pct Analysis & Breakdown",
    "current_value": "0.18",
    "prior_value": "0.14",
    "status": "at_average",
    "verdict": "Your net_margin_pct currently stands at 0.18, operating within normal benchmark boundaries.",
    "historical_trend": [
      {
        "month": "M-4",
        "value": 0.18
      },
      {
        "month": "M-3",
        "value": 0.18
      },
      {
        "month": "M-2",
        "value": 0.18
      },
      {
        "month": "M-1",
        "value": 0.14
      },
      {
        "month": "Current",
        "value": 0.18
      }
    ],
    "drivers": [
      {
        "number": 1,
        "headline": "Accounts Receivable Aging Impact",
        "category": "Receivables",
        "impact_value": "-1.2 pts"
      },
      {
        "number": 2,
        "headline": "Operating Cash Buffer",
        "category": "Liquidity",
        "impact_value": "+0.8 pts"
      }
    ],
    "peer_benchmark": {
      "peer_avg": "39.0%",
      "percentile": "65th percentile",
      "position": "in_line_with_peers"
    },
    "suggested_actions": [
      "Review invoice collection terms to improve working capital.",
      "Maintain target cash reserve buffers."
    ]
  }
}
```

---

## 4. 4. Dashboard Ask AI Advisor (Orchestrator v3.7 — ASK MODE)

- **Status:** `200 PASSED`
- **Method & URL:** `POST /api/dashboard/ask`
- **Response Time:** `24.23s`

**Request Body:**
```json
{
  "question": "How is my cash runway looking for the upcoming season and what should I prioritize?",
  "surface": "dashboard_ask"
}
```

**Response Summary:**
```json
{
  "success": true,
  "data": {
    "chat_id": "1811ceb2-a38b-4411-a91f-0db456f99b62",
    "title": "How is my cash runway looking for the upcoming season and wh...",
    "question": "How is my cash runway looking for the upcoming season and what should I prioritize?",
    "answer": "{\"intent\":\"dashboard_ask\",\"answer\":\"Straight answer: I can't give you a real runway number yet, because the data I have on you right now doesn't support one. Your connected cash balance shows $2,001, revenue month-to-date reads $0, and net margin reads 0%. When cash is that low and no revenue or expense flow is coming through, runway math either divides by zero or spits out a meaningless figure. So rather than hand you a number I'd be making up, here's what's actually going on and what to do about it.\\n\\nTwo possibilities, and they call for very different responses:\\n\\n1) The data is incomplete (most likely). A working Austin barbecue operation with 6 full-time staff, a smoker, a truck, and a catering book does not run on $2,001 with zero revenue posting. That pattern almost always means your accounting connection isn't syncing your operating account, your POS sales aren't flowing in, or the month just reset and nothing's posted yet. If that's the case, your real runway is unknown until the feed is fixed, and fixing it is priority #1 this week. Reconnect QuickBooks (or your accounting tool) and your POS in your LightSignal profile under Integrations, and confirm your main operating account is the one linked, not a secondary or tax account. Once sales and expenses post, I can give you an actual runway figure and break it down by fixed cost vs. variable.\\n\\n2) The data is real. If $2,001 is genuinely all the cash on hand with nothing coming in, that's not a runway question, that's an immediate liquidity situation, and the priority is cash in the door this week: collect any outstanding catering invoices today (barbecue catering usually carries net-15 to net-30 balances you ca
... [truncated for length]
```

---

## 5. 5. Business Health Scorecard (Orchestrator v3.7 — HEALTH NARRATIVE MODE)

- **Status:** `200 PASSED`
- **Method & URL:** `GET /api/ai/health/full`
- **Response Time:** `77.56s`

**Response Summary:**
```json
{
  "success": true,
  "data": {
    "overall": {
      "score": 70,
      "label": "above_average",
      "prior_score": null,
      "peer_avg": null,
      "ai_confidence": 0.5,
      "data_completeness": 50,
      "incomplete_data": true,
      "as_of": "2026-08-28"
    },
    "categories": {
      "financial": {
        "score": 78,
        "label": "above_average",
        "prior_score": null,
        "peer_avg": null,
        "missing": []
      },
      "operational": {
        "score": null,
        "label": null,
        "prior_score": null,
        "peer_avg": null,
        "missing": [
          "pos"
        ]
      },
      "customer": {
        "score": null,
        "label": null,
        "prior_score": null,
        "peer_avg": null,
        "missing": [
          "reviews"
        ]
      },
      "risk": {
        "score": 78,
        "label": "above_average",
        "prior_score": null,
        "peer_avg": null,
        "missing": []
      },
      "growth": {
        "score": 44,
        "label": "at_average",
        "prior_score": null,
        "peer_avg": null,
        "missing": []
      }
    },
    "benchmarks": {
      "peer_pool": "Regional Small Business Pool",
      "peer_avg": null
    },
    "ai_summary": "Business health insights generated successfully.",
    "drivers_display": {
      "positive": [],
      "drags": []
    },
    "watch_areas": [
      {
        "title": "Revenue trend has weakened over recent months, which may impact near-term growth momentum.",
        "description": "Review revenue trend has weakened over recent months, which may impact near-term growth momentum. operating performance.",
        "possible_causes": [],
        "recommended_action": "Put a corrective action in place for revenue trend has weakened over recent months, which may impact near-term growth momentum. this week.",
        "owner_confirmation_prompt": null,
        "learning_id": null
      }
    ],
    "active_alerts": [],
    "data_coverag
... [truncated for length]
```

---

## 6. 6. Research Scout Live Opportunities (Canonical Research Scout V3.1)

- **Status:** `500 FAILED`
- **Method & URL:** `POST /api/ai/opportunities/search`
- **Response Time:** `0.83s`

**Request Body:**
```json
{
  "query": "food festivals and catering vendor opportunities in Austin TX",
  "opportunity_types": [
    "event",
    "festival",
    "catering",
    "vendor_market"
  ],
  "limit": 5
}
```

**Response Summary:**
```json
{
  "error": "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011CeUWbEd836wNcfWWkCT3q'}"
}
```

---

## 7. 7. Business Profile Classification (Canonical Classifier V4.1)

- **Status:** `200 PASSED`
- **Method & URL:** `POST /business-profile/onboarding`
- **Response Time:** `0.9s`

**Request Body:**
```json
{
  "onboarding_data": {
    "business_name": "Lone Star Smokehouse",
    "industry_description": "Barbecue Restaurant & Food Truck",
    "naics_code": "722330",
    "city": "Austin",
    "state": "TX",
    "full_time_employees": 6,
    "main_products": "smoked brisket, pulled pork, craft bbq catering",
    "service_model": "counter_service_and_mobile"
  }
}
```

**Response Summary:**
```json
{
  "success": true,
  "message": "Onboarding data updated successfully",
  "has_existing_data": true,
  "data": {
    "user_id": "0efa55c2-0c81-442c-8e14-706bedc28a46",
    "onboarding_data": {
      "business_name": "Lone Star Smokehouse",
      "industry_description": "Barbecue Restaurant & Food Truck",
      "naics_code": "722330",
      "city": "Austin",
      "state": "TX",
      "full_time_employees": 6,
      "main_products": "smoked brisket, pulled pork, craft bbq catering",
      "service_model": "counter_service_and_mobile",
      "geo": {
        "business_address": "Austin, TX",
        "city": "Austin",
        "state": "TX",
        "latitude": 30.268072,
        "longitude": -97.742806,
        "company_timezone": "America/Chicago",
        "geocode_confidence": "low"
      }
    },
    "business_classifications": [
      "food_hospitality",
      "service_business",
      "small_team"
    ],
    "business_tags": [
      "food_beverage",
      "catering",
      "food_truck"
    ],
    "proven_capabilities": [
      "food_beverage",
      "catering",
      "food_truck"
    ]
  }
}
```

---

## 8. 8. Demand Forecast Generation (Canonical Demand Forecast Analyst v2)

- **Status:** `500 FAILED`
- **Method & URL:** `GET /api/demand-forecast?window=this+weekend`
- **Response Time:** `2.81s`

**Response Summary:**
```json
{
  "detail": "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011CeUWbWUchHqYh8KDaQwLe'}"
}
```

---

