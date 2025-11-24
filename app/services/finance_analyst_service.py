# backend/app/services/finance_analyst_service.py
"""
Finance Analyst Service
Calculates financial KPIs for scenario planning using OpenAI
"""
from typing import Any, Dict, Optional
import json
import os
from openai import AsyncOpenAI


class FinanceAnalystService:
    """
    Finance Analyst agent that calculates scenario KPIs.
    Uses OpenAI to compute ROI, IRR, Payback, DSCR, ICR, Runway.
    """
    
    def __init__(self):
        pass
    
    async def calculate_scenario_kpis(
        self,
        scenario_type: str,
        query: str,
        assumptions: Dict[str, Any],
        baseline_financials: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate financial KPIs for a scenario.
        
        Args:
            scenario_type: Type of scenario (CapEx, Hiring, Pricing, Expansion)
            query: Original user query
            assumptions: Assumptions from Research Scout
            baseline_financials: Current financial state
            business_profile: Business profile data
        
        Returns:
            Dict with baseline, projected, kpis, advisor, visuals, explain_math, why_it_matters
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Build system prompt for Finance Analyst
        system_prompt = f"""You are LightSignal Finance Analyst, an expert financial modeling agent.

Your mission: Calculate precise financial KPIs for business scenario planning.

🧮 CORE CALCULATIONS

- **ROI** = ((NetGain) ÷ Cost) × 100
- **IRR** = Internal rate where NPV = 0 (use financial formulas)
- **Payback** = Cost ÷ AnnualCashFlow (years)
- **DSCR** = EBITDA ÷ DebtService
- **ICR** = EBIT ÷ InterestExpense
- **Runway** = Cash ÷ MonthlyBurn (months)
- **Runway Delta** = Projected Runway - Baseline Runway

📊 INPUTS

- **Scenario Type**: {scenario_type}
- **User Query**: "{query}"
- **Assumptions**: {json.dumps(assumptions, default=str)}
- **Baseline Financials**: {json.dumps(baseline_financials, default=str)}
- **Business Profile**: {json.dumps(business_profile, default=str) if business_profile else "None"}

🎯 OUTPUT FORMAT — STRICT JSON ONLY

Return one object shaped as:

{{
  "baseline": {{
    "cash": 0.0,
    "revenue": 0.0,
    "expenses": 0.0,
    "ebitda": 0.0,
    "ebit": 0.0,
    "debt_service": 0.0,
    "interest_expense": 0.0,
    "monthly_burn": 0.0
  }},
  "projected": {{
    "cash": 0.0,
    "revenue": 0.0,
    "expenses": 0.0,
    "ebitda": 0.0,
    "ebit": 0.0,
    "debt_service": 0.0,
    "interest_expense": 0.0,
    "monthly_burn": 0.0
  }},
  "kpis": {{
    "roi": 0.0,
    "irr": 0.0,
    "payback_years": 0.0,
    "dscr": 0.0,
    "icr": 0.0,
    "runway_months": 0.0,
    "runway_delta_months": 0.0,
    "cash_delta": 0.0
  }},
  "advisor": {{
    "summary": "1-2 sentences synthesizing the scenario impact.",
    "actions": [
      {{"title": "Action 1", "impact": "quantified impact", "priority": "high|medium|low", "reason": "why"}},
      {{"title": "Action 2", "impact": "quantified impact", "priority": "high|medium|low", "reason": "why"}},
      {{"title": "Action 3", "impact": "quantified impact", "priority": "high|medium|low", "reason": "why"}}
    ],
    "risks": [
      {{"level": "low|med|high", "message": "specific risk"}},
      {{"level": "low|med|high", "message": "specific risk"}}
    ]
  }},
  "visuals": [
    {{
      "type": "comparison",
      "data": {{
        "baseline": {{"cash": 0, "revenue": 0, "expenses": 0}},
        "projected": {{"cash": 0, "revenue": 0, "expenses": 0}}
      }}
    }},
    {{
      "type": "waterfall",
      "data": {{
        "categories": ["Starting Cash", "Revenue Change", "Expense Change", "Ending Cash"],
        "values": [0, 0, 0, 0]
      }}
    }}
  ],
  "explain_math": "Step-by-step calculation explanation showing how each KPI was derived.",
  "why_it_matters": "Business impact explanation in plain English."
}}

⚙️ BEHAVIOR RULES

- Use realistic financial assumptions based on the scenario type and business profile.
- If baseline financials are incomplete, make conservative estimates and note them.
- All KPIs must be calculated and populated (no null values unless truly not applicable).
- Advisor actions should be specific, actionable, and prioritized.
- explain_math should show the actual formulas and numbers used.
- why_it_matters should explain the business impact in owner-friendly language.
- For IRR, if the scenario doesn't have cash flows over time, estimate based on annual returns.
- For Payback, if annual cash flow is zero or negative, set to null or a very high number.

✅ QUALITY CHECK BEFORE RETURN

- All KPIs are calculated and reasonable.
- Advisor has at least 3 specific actions.
- Visuals include comparison and waterfall charts.
- explain_math is detailed and shows formulas.
- why_it_matters is clear and actionable.

JSON only (no Markdown, no prose outside fields).
"""

        # Call OpenAI
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Calculate KPIs for this scenario: {query}"}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from Finance Analyst")
