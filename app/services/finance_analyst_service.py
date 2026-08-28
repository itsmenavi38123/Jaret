# backend/app/services/finance_analyst_service.py
"""
Finance Analyst Service
Calculates financial KPIs, generates dashboard analysis, financial overview insights, and scenario impacts using Claude.
"""
from typing import Any, Dict, Optional, List
import json
import re
from app.services.claude_service import claude_service
from app.services.lightsignal_memory_tool import LightSignalMemoryTool

from app.services.financial_overview_drawer_prompt import (
    get_financial_analyst_prompt,
    FINANCIAL_OVERVIEW_DRAWER_PROMPT,
)
from app.services.scenario_lab_prompt import get_scenario_lab_prompt


class FinanceAnalystService:
    """
    Finance Analyst agent that handles financial overview insights, dashboard analysis,
    KPI explanations, and scenario calculations.
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
        Generate dashboard insights and alerts from KPI data using Canonical FA V6 (DASHBOARD MODE).
        
        Args:
            context: Dict with current_period, prior_period, breakdown, flags
            classifier_output: Rich business classifier output
            user_id: User ID
        
        Returns:
            Dict with summary, alerts, insight_pairs, opportunities, what_changed, missing_data_notice
        """
        system_prompt = get_financial_analyst_prompt()
        
        return await claude_service.json_completion(
            system_prompt=system_prompt,
            user_content={
                "request": "Generate dashboard analysis. Output ONLY valid JSON.",
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
        Generate Financial Overview (INSIGHTS MODE) hero stage + swipe cards payload using Canonical FA V6.
        Includes profitability status banner and 3-12 insight cards with 4 accordions & animation directives.
        """
        system_prompt = get_financial_analyst_prompt()

        return await claude_service.json_completion(
            system_prompt=system_prompt,
            user_content={
                "request": "Generate financial overview insights. Output ONLY valid JSON.",
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
        Calculate financial KPIs for a scenario using Canonical LightSignal Scenario Lab v1.4.
        
        Args:
            scenario_type: Type of scenario (CapEx, Hiring, Pricing, Expansion)
            query: Original user query
            assumptions: Assumptions from Research Scout
            baseline_financials: Current financial state
            business_profile: Business profile data
            classifier_output: Rich business classifier output
        
        Returns:
            Dict with baseline, projected, kpis, advisor, visuals, explain_math, why_it_matters
        """
        memory_tool = LightSignalMemoryTool(user_id=user_id)

        system_prompt = get_scenario_lab_prompt()

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
        why_reason_codes: List[Dict[str, Any]],
    ) -> str:
        """
        Generate plain-text bullets explaining why an opportunity was suggested using Canonical FA V6 (OPPORTUNITY WHY SUGGESTED MODE).
        """
        system_prompt = get_financial_analyst_prompt()

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
        why_reason_codes: List[Dict[str, Any]],
    ) -> str:
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


# Global singleton instance
finance_analyst_service = FinanceAnalystService()
