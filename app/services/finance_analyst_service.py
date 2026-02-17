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
    
    async def analyze_dashboard(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate dashboard insights and alerts from KPI data.
        
        Args:
            context: Dict with current_period, prior_period, breakdown, flags
        
        Returns:
            Dict with summary, alerts, insight_pairs, opportunities, what_changed
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Build system prompt for dashboard analysis
        system_prompt = """You are LightSignal Finance Analyst, an expert at analyzing business financials.

Your mission: Generate actionable dashboard insights from KPI data.

📊 CURRENT & PRIOR PERIOD DATA

You will receive:
- current_period: Latest KPI snapshot (revenue, expenses, margins, cash, runway, ratios, AR metrics)
- prior_period: Prior period comparison data (same metrics for trend analysis)
- breakdown: Optional revenue by segment/product, expenses by category
- flags: Pre-calculated boolean alerts (low_runway, negative_cash_flow, revenue_decline, margin_compression, ar_aging_issue)

🎯 OUTPUT FORMAT — STRICT JSON ONLY

Return one object shaped exactly as:

{
  "summary": "One concise sentence synthesizing the overall health and primary concern",
  "alerts": [
    {
      "severity": "high|medium|low",
      "message": "Specific, actionable message with numbers",
      "icon": "⚠️|📊|✅",
      "type": "risk|warning|positive"
    }
  ],
  "insight_pairs": [
    {
      "problem": "Specific problem statement with quantified impact",
      "solution": "Specific, actionable solution with measurable outcome"
    }
  ],
  "opportunities": [
    "Specific growth opportunity with revenue/segment details"
  ],
  "what_changed": [
    "Key metric changed from X to Y with dollar or percentage impact"
  ]
}

⚙️ BEHAVIOR RULES

- summary: 1 sentence max, highlight biggest concern or strength
- alerts: Return 3-5 alerts. Order by severity (high first). Mix risk + positives. Use precise numbers.
- insight_pairs: Return 2-3 pairs. Each pair has a problem + its solution. Problems linked to flags. Solutions are specific/biz-friendly.
- opportunities: Return 1-2 growth opportunities. Reference segments/products if available in breakdown.
- what_changed: Return 2-3 key metric changes with specific numbers and impact.

KEY RULES:
- Identify problems from flags (low_runway → AR aging issue → negative cash flow)
- Pair each problem with a specific, actionable solution
- Use segment/product data to personalize insights
- Highlight revenue growth opportunities detected in breakdown
- Always use specific numbers and percentages (no vague statements)
- Problem + solution must be related (they're in same object for a reason)

✅ QUALITY CHECK BEFORE RETURN

- summary is 1 sentence, specific, actionable
- All 3+ alerts have severity, message with numbers, icon, type
- All insight_pairs have related problem + solution (not random)
- All opportunities reference segments or products from breakdown
- All what_changed entries have specific numbers and context

JSON only (no Markdown, no prose outside fields).
"""
        
        # Call OpenAI
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this dashboard data and generate insights: {json.dumps(context, default=str)}"}
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


# Global singleton instance
finance_analyst_service = FinanceAnalystService()
