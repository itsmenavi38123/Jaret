from __future__ import annotations

from datetime import date
import calendar
from typing import List, Dict, Any

import numpy as np
from statsmodels.tsa.seasonal import STL
from sklearn.metrics import r2_score

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
import json
from openai import OpenAI
from app.db import get_collection

from app.config import JWT_SECRET, JWT_ALGORITHM
from app.services.quickbooks_token_service import quickbooks_token_service
from app.services.quickbooks_financial_service import quickbooks_financial_service


router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

security = HTTPBearer()


FULL_SYSTEM_PROMPT = """
You are the Demand Forecast Analyst for LightSignal.

Your job is to convert backend forecast metrics into structured, UI-ready JSON that strictly follows the frontend schema.

You MUST return ONLY valid JSON.
Do NOT return markdown.
Do NOT wrap JSON in code blocks.
Do NOT include commentary outside JSON.
Do NOT modify, round, approximate, or invent backend numeric values.

========================================
ABSOLUTE ENFORCEMENT RULES
========================================

1. Numerical Fidelity
- Use backend numbers EXACTLY as provided.
- Do NOT recalculate.
- Do NOT estimate.
- Do NOT introduce new numeric values.

2. Strict Root Structure
You MUST return EXACTLY these top-level keys:

{
  "demand_outlook": {},
  "chart_annotations": {},
  "drivers": {},
  "demand_concentration": {},
  "preparation_guidance": {}
}

No extra keys.
No missing keys.
No renaming.

========================================
ENUM LOCK (MANDATORY)
========================================

risk_level MUST be:
- "Stable"
- "Moderate"
- "Volatile"

model_confidence MUST be:
- "High"
- "Medium"
- "Low"

volatility_level MUST be:
- "Low"
- "Medium"
- "High"

confidence_badge MUST be:
- "High"
- "Medium"
- "Low"

direction_label MUST be:
- "Up"
- "Down"
- "Flat"

If any other value is used → output is invalid.

========================================
STRUCTURE LOCK (CRITICAL)
========================================

❗ NEVER place drawer_content at root level of demand_concentration.

❗ NEVER leave items array empty when is_applicable = true.

❗ NEVER return string where object is required.

❗ NEVER omit required nested keys.

----------------------------------------
demand_outlook
----------------------------------------

Must contain:

PAGE:
- outlook_text
- risk_level
- model_confidence
- volatility_level

DRAWERS:
- risk_level_drawer
- model_confidence_drawer
- volatility_level_drawer

Each drawer MUST contain:
{
  "explanation": "...",
  "what_this_means": "...",
  "metrics_breakdown": [
      {
          "metric": "...",
          "value": "...",
          "interpretation": "...",
          "calculation": "..."
      }
  ],
  "risk_factors_to_watch": []
}

metrics_breakdown MUST NOT be empty.

----------------------------------------
drivers
----------------------------------------

Must contain:

{
  "local_events": [],
  "weather": {},
  "seasonality": {},
  "peer_context": {}
}

----------------------------------------
LOCAL EVENTS
----------------------------------------

Each event MUST contain:

PAGE:
- name
- date_range
- description
- confidence_badge

DRAWER:
- drawer_content:
  {
    "detailed_description": "...",
    "impact_calculation": "...",
    "preparation_checklist": [],
    "what_could_change": []
  }

----------------------------------------
WEATHER
----------------------------------------

Backend sends weather.is_applicable flag.

IF true:
Return EXACTLY:

{
  "is_applicable": true,
  "influence_label": "High|Moderate|Low",
  "brief_explanation": "...",
  "influence_tooltip": "...",
  "drawer_content": {
      "detailed_explanation": "...",
      "how_we_calculate_influence": {
          "step_1": "...",
          "step_1_detail": "...",
          "step_2": "...",
          "step_2_detail": "..."
      },
      "weather_forecast_details": {},
      "what_this_means_for_planning": []
  }
}

IF false:
Return ONLY:

{
  "is_applicable": false,
  "not_applicable_drawer": {
      "explanation": "..."
  }
}

Do NOT include influence_label if not applicable.

----------------------------------------
SEASONALITY
----------------------------------------

Must contain:

PAGE:
- effect_description

DRAWER:
- drawer_content:
  {
    "detailed_explanation": "...",
    "how_we_calculate_seasonality": {},
    "pattern_reliability": "...",
    "note_about_weather": "..."
  }

----------------------------------------
PEER CONTEXT
----------------------------------------

Must contain:

PAGE:
- summary

DRAWER:
- drawer_content:
  {
    "detailed_comparison": "...",
    "peer_cohort_details": {
        "description": "...",
        "sample_size": "..."
    }
  }

peer_cohort_details MUST be an OBJECT, not string.

----------------------------------------
demand_concentration
----------------------------------------

Must ALWAYS include:
- is_applicable

IF is_applicable = true:

Return:

{
  "is_applicable": true,
  "items": [
      {
          "name": "...",
          "direction_label": "Up|Down|Flat",
          "confidence_badge": "High|Medium|Low",
          "brief_explanation": "...",
          "drawer_content": {
              "detailed_explanation": "...",
              "trend_calculation": "...",
              "preparation_specific": "...",
              "what_could_change": "..."
          }
      }
  ]
}

Each item MUST include drawer_content.
items array MUST NOT be empty.

IF is_applicable = false:

Return ONLY:

{
  "is_applicable": false,
  "not_applicable_drawer": {
      "explanation": "...",
      "how_to_enable": []
  }
}

----------------------------------------
preparation_guidance
----------------------------------------

PAGE:
- headline
- staffing_capacity []
- inventory_supply []
- operational_risk_notes []

DRAWERS:

staffing_drawer:
{
  "detailed_calculation": "...",
  "cost_benefit_analysis": "...",
  "risk_of_understaffing": "...",
  "recommended_action": "..."
}

inventory_drawer:
{
  "detailed_calculation": "...",
  "lead_time_risk": "...",
  "specific_reorder_points": "..."
}

operational_drawer:
{
  "weather_volatility_explained": "...",
  "event_clustering_risk": "..."
}

preparation_window:
{
  "brief": "...",
  "detailed_timeline": []
}

model_confidence_note:
{
  "brief": "...",
  "drawer_explanation": "..."
}

adaptation_note:
{
  "brief": "...",
  "drawer_explanation": "..."
}

========================================
DEPTH ENFORCEMENT
========================================

- PAGE text = max 2 sentences.
- DRAWER text = detailed, multi-sentence explanation.
- metrics_breakdown MUST contain real metrics.
- Never return empty required arrays.
- Never return placeholder text.

========================================
FINAL VALIDATION
========================================

Before returning:

✔ All required keys exist
✔ All enums valid
✔ All required nested fields exist
✔ No misplaced drawer_content
✔ No empty items when is_applicable = true
✔ No extra root keys

Return ONLY valid JSON.
"""

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        return user_id

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def _last_day_of_month(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last_day)


async def _fetch_last_year_revenue(user_id: str) -> List[float]:

    tokens = await quickbooks_token_service.get_tokens_by_user(user_id)
    active_tokens = [t for t in tokens if t.is_active]

    if not active_tokens:
        return []

    today = date.today()
    first_of_this_month = _first_day_of_month(today)

    start = _add_months(first_of_this_month, -11)
    end = _last_day_of_month(today)

    sales = await quickbooks_financial_service.get_historical_sales(
        user_id=user_id,
        start_date=start,
        end_date=end,
        granularity="monthly",
    )

    historical_revenue = [
        float(item.get("revenue") or 0.0)
        for item in sales
    ]

    return historical_revenue

def _calculate_forecast_metrics(historical_revenue: List[float]) -> Dict[str, Any]:

    data_points = len(historical_revenue)

    if data_points < 3:
        industry_median = 45000.0
        return {
            "model_type": "IndustryBenchmark",
            "pct_change_30d": 0.0,
            "forecast_next_30d": industry_median,
            "current_30d": 0.0,
            "r_squared": 0.30,
            "confidence_score": 0.30,
            "volatility_score": 0.50,
            "forecast_series": [industry_median] * 6,
        }

    series = np.array(historical_revenue)


    if data_points >= 12:

        stl = STL(series, period=12)
        result = stl.fit()

        trend = result.trend
        seasonal = result.seasonal

        growth_rate = (
            (trend[-1] - trend[-2]) / trend[-2]
            if trend[-2] != 0 else 0.0
        )

        forecast_next = series[-1] * (1 + growth_rate)

        fitted = trend + seasonal
        r2 = r2_score(series, fitted)

        confidence_score = max(0.0, min(1.0, float(r2)))

        mean_val = np.mean(series)
        volatility_score = (
            float(np.std(series) / mean_val) if mean_val != 0 else 0.0
        )

        current_revenue = series[-1]

        pct_change_30d = (
            ((forecast_next - current_revenue) / current_revenue) * 100
            if current_revenue != 0 else 0.0
        )

        forecast_series = []
        last_value = current_revenue
        for _ in range(6):
            next_val = last_value * (1 + growth_rate)
            forecast_series.append(round(float(next_val), 2))
            last_value = next_val

        return {
            "model_type": "STL",
            "pct_change_30d": round(float(pct_change_30d), 2),
            "forecast_next_30d": round(float(forecast_next), 2),
            "current_30d": round(float(current_revenue), 2),
            "r_squared": round(float(r2), 2),
            "confidence_score": round(float(confidence_score), 2),
            "volatility_score": round(float(volatility_score), 4),
            "forecast_series": forecast_series,
        }


    if 6 <= data_points <= 11:

        x = np.arange(data_points)
        y = series

        slope, intercept = np.polyfit(x, y, 1)

        next_month = data_points
        forecast_next = slope * next_month + intercept

        predictions = slope * x + intercept
        r2 = r2_score(y, predictions)

        std_dev = np.std(y - predictions)

        confidence_score = max(0.0, min(1.0, float(r2)))

        mean_val = np.mean(series)
        volatility_score = (
            float(np.std(series) / mean_val) if mean_val != 0 else 0.0
        )

        current_revenue = series[-1]

        pct_change_30d = (
            ((forecast_next - current_revenue) / current_revenue) * 100
            if current_revenue != 0 else 0.0
        )

        forecast_series = []
        last_index = next_month
        for _ in range(6):
            next_val = slope * last_index + intercept
            forecast_series.append(round(float(next_val), 2))
            last_index += 1

        return {
            "model_type": "LinearTrend",
            "pct_change_30d": round(float(pct_change_30d), 2),
            "forecast_next_30d": round(float(forecast_next), 2),
            "current_30d": round(float(current_revenue), 2),
            "r_squared": round(float(r2), 2),
            "confidence_score": round(float(confidence_score), 2),
            "volatility_score": round(float(volatility_score), 4),
            "forecast_series": forecast_series,
        }


    mean_val = np.mean(series)
    std_dev = np.std(series)

    forecast_next = mean_val

    cv = std_dev / mean_val if mean_val != 0 else 0

    if cv < 0.15:
        confidence_score = 0.55
    elif cv < 0.30:
        confidence_score = 0.45
    else:
        confidence_score = 0.35

    current_revenue = series[-1]

    pct_change_30d = (
        ((forecast_next - current_revenue) / current_revenue) * 100
        if current_revenue != 0 else 0.0
    )

    return {
        "model_type": "MovingAverage",
        "pct_change_30d": round(float(pct_change_30d), 2),
        "forecast_next_30d": round(float(forecast_next), 2),
        "current_30d": round(float(current_revenue), 2),
        "r_squared": round(float(confidence_score), 2),
        "confidence_score": round(float(confidence_score), 2),
        "volatility_score": round(float(cv), 4),
        "forecast_series": [round(float(mean_val), 2)] * 6,
    }



async def _call_ai_agent(payload: Dict[str, Any]) -> Dict[str, Any]:

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": FULL_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    parsed = json.loads(content)

    required_keys = [
        "demand_outlook",
        "chart_annotations",
        "drivers",
        "demand_concentration",
        "preparation_guidance",
    ]

    for key in required_keys:
        if key not in parsed:
            raise Exception(f"Missing key in AI output: {key}")

    valid_risk = {"Stable", "Moderate", "Volatile"}
    valid_confidence = {"High", "Medium", "Low"}
    valid_volatility = {"Low", "Medium", "High"}
    valid_direction = {"Up", "Down", "Flat"}

    demand_outlook = parsed.get("demand_outlook")

    if not demand_outlook:
        raise Exception("Missing demand_outlook")

    if "PAGE" in demand_outlook:
        demand_page = demand_outlook.get("PAGE", {})
    else:
        demand_page = demand_outlook

    risk_level = demand_page.get("risk_level")
    model_confidence = demand_page.get("model_confidence")
    volatility_level = demand_page.get("volatility_level")

    if risk_level not in valid_risk:
        raise Exception("Invalid or missing risk_level enum")

    if model_confidence not in valid_confidence:
        raise Exception("Invalid or missing model_confidence enum")

    if volatility_level not in valid_volatility:
        raise Exception("Invalid or missing volatility_level enum")
    
    dc = parsed["demand_concentration"]

    if dc.get("is_applicable") is True:
        if not dc.get("items"):
            raise Exception("is_applicable=True but items array is empty")

        for item in dc["items"]:
            if item["direction_label"] not in valid_direction:
                raise Exception("Invalid direction_label enum")

    return parsed
   

@router.get("/demand-forecast")
async def demand_forecast_route(user_id: str = Depends(get_current_user)):

    business_profiles = get_collection("business_profiles")
    business_profile = await business_profiles.find_one({"user_id": user_id})

    if not business_profile:
        raise HTTPException(
            status_code=400,
            detail="Business profile not found. Please complete onboarding."
        )

    try:
        historical_revenue = await _fetch_last_year_revenue(user_id)

        # Tiered forecasting handled inside this function
        metrics = _calculate_forecast_metrics(historical_revenue)

        weather_applicable = True
        item_tracking_enabled = True

        flags = {
            "weather_applicable": weather_applicable,
            "item_tracking_enabled": item_tracking_enabled,
        }

        ai_input = {
            "business_context": {
                "business_type": business_profile.get("business_type")
            },
            "metrics": metrics,
            "model_metadata": {
                "model_type": metrics.get("model_type")
            },
            "drivers_input": {
                "weather": {
                    "is_applicable": weather_applicable
                }
            },
            "demand_concentration_input": {
                "is_applicable": item_tracking_enabled
            }
        }

        agent_output = await _call_ai_agent(ai_input)

        return {
            "metrics": metrics,
            "flags": flags,
            "data": {
                "historical_revenue": historical_revenue,
                "forecast_series": metrics.get("forecast_series", []),
            },
            "agentOutput": agent_output,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))