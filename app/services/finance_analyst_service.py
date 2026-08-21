# backend/app/services/finance_analyst_service.py
"""
Finance Analyst Service
Calculates financial KPIs for scenario planning using Claude.
"""
from typing import Any, Dict, Optional
import json
import re
from app.services.claude_service import claude_service
from app.services.lightsignal_memory_tool import LightSignalMemoryTool

from app.services.financial_overview_drawer_prompt import (
    FINANCIAL_OVERVIEW_DRAWER_PROMPT,
)

class FinanceAnalystService:
    """
    Finance Analyst agent that calculates scenario KPIs.
    Uses Claude to compute ROI, IRR, Payback, DSCR, ICR, Runway.
    """
    
    def __init__(self):
        pass
    
    async def analyze_dashboard(
        self,
        context: Dict[str, Any],
        classifier_output: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate dashboard insights and alerts from KPI data.
        
        Args:
            context: Dict with current_period, prior_period, breakdown, flags
        
        Returns:
            Dict with summary, alerts, insight_pairs, opportunities, what_changed
        """
        # Build system prompt for dashboard analysis
        system_prompt = """You are LightSignal Finance Analyst, an expert at analyzing business financials.

Your mission: Generate actionable dashboard insights from KPI data.

📊 CURRENT & PRIOR PERIOD DATA

You will receive:
- current_period: Latest KPI snapshot (revenue, expenses, margins, cash, runway, ratios, AR metrics)
- prior_period: Prior period comparison data (same metrics for trend analysis)
- breakdown: Optional revenue by segment/product, expenses by category
- flags: Pre-calculated boolean alerts (low_runway, negative_cash_flow, revenue_decline, margin_compression, ar_aging_issue)

🎯 OUTPUT FORMAT — STRICT JSON ONLY (FA V6 Schema)

Return one object shaped exactly as:

{
  "summary": "One concise sentence synthesizing overall business health and primary concern (≤150 chars)",
  "alerts": [
    {
      "severity": "critical|below_average|above_average",
      "type": "risk|warning|positive",
      "message": "Specific, actionable message with numbers (≤60 chars)",
      "icon": "🔴|🟡|🟢"
    }
  ],
  "insight_pairs": [
    {
      "head": "Short headline (≤60 chars)",
      "problem": "Specific problem statement with quantified impact (≤200 chars)",
      "solution": "Actionable solution with measurable outcome (≤200 chars)"
    }
  ],
  "opportunities": [
    {
      "head": "Short headline (≤60 chars)",
      "body": "Specific growth opportunity with revenue/segment details (≤200 chars)"
    }
  ],
  "what_changed": [
    "Key metric change from X to Y with dollar or percentage impact (≤150 chars)"
  ],
  "missing_data_notice": null
}

⚙️ BEHAVIOR RULES

- summary: 1 sentence max (≤150 chars), highlight biggest concern or strength.
- alerts: Return 3-5 alerts. Severity MUST be "critical", "below_average", or "above_average". Order critical first.
- insight_pairs: Return 2-3 pairs with head, problem, solution.
- opportunities: Return 1-2 growth opportunities with head and body.
- what_changed: Return 2-3 key metric changes.
- missing_data_notice: null unless data is missing/incomplete.

JSON only (no Markdown, no prose outside fields).
"""
        
        return await claude_service.json_completion(
            system_prompt=system_prompt,
            user_content={
                "context": context,
                "classifier_output": classifier_output,
            },
            temperature=0.2,
            max_tokens=4000,
        )

    async def generate_financial_overview_insights(
        self,
        financial_overview: Dict[str, Any],
        business_health: Dict[str, Any],
        classifier_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Financial Overview (INSIGHTS MODE) hero stage + swipe cards payload.
        Includes profitability status banner and 3-12 insight cards with 4 accordions & animation directives.
        """
        system_prompt = """You are LightSignal Finance Analyst operating in INSIGHTS MODE (Financial Overview tab).

Your mission: Generate the MECHANIC-frame Financial Overview insights block (profitability status banner + pressing & stable insight cards).

🎯 OUTPUT FORMAT — STRICT JSON ONLY

Return one object shaped exactly as:

{
  "profitability_status_banner": {
    "verdict": "One clear sentence overall profit read (e.g. 'You're okay — 1 thing needs you this week.')",
    "subhead": "Distinct subhead explaining the position (e.g. 'Profitable, with healthy margins. Everything else is on track.')",
    "status": "top_tier|above_average|at_average|below_average|critical",
    "updated_text": "Updated 2h ago · QuickBooks synced"
  },
  "insights": [
    {
      "id": "unique_snake_case_id",
      "headline": "Punchy headline (≤80 chars)",
      "tier": "tier_1|tier_2",
      "pressing_score": 48,
      "sev": "crit|build|stable|good",
      "status_label": "PRESSING NOW|BUILDING|WORTH KNOWING|STABLE|RESOLVED",
      "alert": "Short formatted metric alert string (e.g. '$48K · 52-day DSO')",
      "whats_going_on": "Detailed explanation of what is happening in the business (≤280 chars)",
      "why_it_matters_now": "Why this matters to the owner right now (≤240 chars)",
      "what_to_do": "Specific operational recommendation (≤280 chars)",
      "expected_impact": {
        "value_text": "Formatted impact (e.g. '+$8K · +7d runway')",
        "calculation_basis": "Math calculation line footnote (≤200 chars)"
      },
      "effort": "quick_win|moderate|heavy",
      "confidence": "high|moderate|low",
      "action_buttons": [
        {
          "label": "Dynamic actionable CTA label (e.g. 'Draft early-pay emails' / 'Review vendor terms')",
          "type": "primary_cta",
          "action": "open_action_modal"
        },
        {
          "label": "Snooze",
          "type": "snooze",
          "action": "snooze"
        }
      ],
      "directive": {
        "signal_id": "ar_aging|cash_burn|margin_drop|revenue_growth",
        "shape_id": "shape_12_waterfall|shape_01_gauge|shape_04_trend",
        "theme": "red|amber|white|green",
        "labels": {
          "banner": "CATEGORY BANNER (≤30 chars)",
          "alert_value": "$48K · 52-day DSO"
        }
      }
    }
  ],
  "missing_data_notice": null
}

⚙️ BEHAVIOR RULES:
- Generate 3 to 6 insights ranked by pressing_score descending.
- Ensure every insight has all 4 accordion fields (whats_going_on, why_it_matters_now, what_to_do, expected_impact).
- Include specific numbers, dollars, and days in every item.
- Strict JSON output only.
"""

        return await claude_service.json_completion(
            system_prompt=system_prompt,
            user_content={
                "financial_overview": financial_overview,
                "business_health": business_health,
                "classifier_output": classifier_output,
            },
            temperature=0.2,
            max_tokens=4000,
        )

    
    async def calculate_scenario_kpis(
        self,
        scenario_type: str,
        user_id: str,
        query: str,
        assumptions: Dict[str, Any],
        baseline_financials: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]] = None,
        classifier_output: Optional[Dict[str, Any]] = None,
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
        memory_tool = LightSignalMemoryTool(user_id=user_id)

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

        return await claude_service.json_completion(
            system_prompt=system_prompt,
            user_content={
                "query": query,
                "scenario_type": scenario_type,
                "assumptions": assumptions,
                "baseline_financials": baseline_financials,
                "business_profile": business_profile,
                "classifier_output": classifier_output,
            },
            temperature=0.2,
            max_tokens=4000,
        )
    
    async def generate_opportunity_why_suggested(
        self,
        why_reason_codes,
    ):


        system_prompt = """
          You are LightSignal Financial Analyst.

          MODE: opportunity_why_suggested

          You receive a why_reason_codes array.

          Rules:
          - Convert each code to exactly ONE bullet.
          - Use only values found inside the data object.
          - Never invent numbers.
          - Never add extra bullets.
          - Never add advice, commentary, recommendations, or strategy.
          - Keep each bullet factual and brief.
          - Output plain text bullets only.
          """

        output = await claude_service.text_completion(
            system_prompt=system_prompt,
            user_content={
                "mode": "opportunity_why_suggested",
                "why_reason_codes": why_reason_codes,
            },
            temperature=0.2,
            max_tokens=2000,
        )

        validated = self.validate_why_suggested_output(
            output,
            why_reason_codes,
        )

        return validated
    

    def validate_why_suggested_output(
        self,
        output: str,
        why_reason_codes,
    ):
        allowed_numbers = []
        for item in why_reason_codes:
            data = item.get("data", {})
            for value in data.values():
                if isinstance(value, (int, float)):
                    allowed_numbers.append(str(value))

        detected_numbers = re.findall(r"\d+(?:\.\d+)?", output)
        corrected_output = output

        for number in detected_numbers:
            if number not in allowed_numbers:
                corrected_output = corrected_output.replace(
                    number,
                    "[value]",
                )
                print(f"AgentOutputValidator replaced invalid number: {number}")

        bullets = [
            line for line in corrected_output.split("\n")
            if line.strip()
        ]

        max_bullets = len(why_reason_codes)

        if len(bullets) > max_bullets:

            bullets = bullets[:max_bullets]

            print("AgentOutputValidator removed extra bullets")

        return "\n".join(bullets)


    async def generate_financial_overview_insights(
        self,
        financial_overview: Dict[str, Any],
        business_health: Dict[str, Any],
        classifier_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        system_prompt = f"""
          You are LightSignal Financial Analyst.

          MODE: financial_overview_insights

          Output ONLY valid JSON.

          Return EXACTLY this schema:

          {{
            "profitability_banner": {{
              "status": "top_tier | above_average | at_average | below_average | critical | null",
              "headline": "",
              "supporting_text": "",
              "missing_data_notice": null
            }},
            "items": [
              {{
                "signal_id": "",
                "pressing_score": 0,
                "tier": "tier_1 | tier_2",
                "headline": "",
                "whats_going_on": "",
                "why_it_matters_now": "",
                "what_to_do": "",
                "expected_impact": {{
                  "value_text": "",
                  "calculation_basis": ""
                }},
                "effort": "quick_win | moderate | heavy",
                "confidence": "high | moderate | low",
                "directive": {{
                  "shape_id": "",
                  "fallback": false,
                  "state": "",
                  "theme": {{}},
                  "numbers": {{}},
                  "labels": {{}}
                }}
              }}
            ],
            "missing_data_notice": null
          }}

          Rules:
          - Follow Financial Analyst Prompt V6 INSIGHTS MODE.
          - Return only JSON.
          - No markdown.
          - No explanations outside JSON.
          - Rank items by pressing_score descending.
          - Set tier_1 when pressing_score >= 30.
          - Set tier_2 when pressing_score < 30.
          - Use business_health financial signals when available.
          - Use classifier_output when available.
          - Do not invent metrics not present in the payload.
          - Return between 3 and 12 insight items when sufficient data exists.

          {FINANCIAL_OVERVIEW_DRAWER_PROMPT}
          """

        return await claude_service.json_completion(
            system_prompt=system_prompt,
            user_content={
                "financial_overview": financial_overview,
                "business_health": business_health,
                "classifier_output": classifier_output,
            },
            temperature=0.2,
            max_tokens=4000,
        )

    
# Global singleton instance
finance_analyst_service = FinanceAnalystService()
