# backend/app/services/orchestrator_service.py
"""
Orchestrator Service
Coordinates the multi-agent workflow for scenario planning
"""
from typing import Any, Dict, List, Optional
import json
import os
from openai import AsyncOpenAI

from app.services.research_scout_service import ResearchScoutService
from app.services.finance_analyst_service import FinanceAnalystService


class OrchestratorService:
    """
    Orchestrator agent that coordinates scenario planning workflow.
    Classifies scenario type, calls Research Scout for priors, and Finance Analyst for KPIs.
    """
    
    def __init__(self):
        self.research_scout = ResearchScoutService()
        self.finance_analyst = FinanceAnalystService()
    
    async def classify_scenario(self, query: str) -> str:
        """
        Classify the scenario type from user query.
        
        Args:
            query: User's free-text query
        
        Returns:
            Scenario type: CapEx|Hiring|Pricing|Expansion|Other
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        client = AsyncOpenAI(api_key=api_key)
        
        system_prompt = """You are a scenario classification expert.

            Given a business scenario query, classify it into one of these types:
            - **CapEx**: Capital expenditure (equipment, vehicles, property, major purchases)
            - **Hiring**: Adding staff, contractors, or labor
            - **Pricing**: Changing prices, discounts, or pricing strategy
            - **Expansion**: Opening new locations, entering new markets, scaling operations
            - **Other**: Anything else

            Return ONLY the scenario type as a single word: CapEx, Hiring, Pricing, Expansion, or Other.
        """

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
        )
        
        scenario_type = response.choices[0].message.content.strip()
        return scenario_type
    
    async def orchestrate_scenario_planning(
        self,
        query: str,
        user_id: str,
        business_profile: Optional[Dict[str, Any]] = None,
        opportunities_profile: Optional[Dict[str, Any]] = None,
        baseline_financials: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main orchestration workflow for scenario planning.
        
        Args:
            query: User's scenario query
            user_id: User ID
            business_profile: Business profile data
            opportunities_profile: Opportunities profile data
            baseline_financials: Current financial state from QuickBooks/Xero
        
        Returns:
            Complete scenario response with KPIs, advisor, visuals
        """
        # Step 1: Classify scenario type
        scenario_type = await self.classify_scenario(query)
        
        # Step 2: Get assumptions from Research Scout
        assumptions_data = await self.research_scout.get_scenario_priors(
            scenario_type=scenario_type,
            query=query,
            business_profile=business_profile,
        )
        
        assumptions = assumptions_data.get("assumptions", [])
        sources = assumptions_data.get("sources", [])
        
        # Convert assumptions list to dict for Finance Analyst
        assumptions_dict = {a["key"]: a["value"] for a in assumptions}
        
        # Step 3: Calculate KPIs with Finance Analyst
        financial_result = await self.finance_analyst.calculate_scenario_kpis(
            scenario_type=scenario_type,
            query=query,
            assumptions=assumptions_dict,
            baseline_financials=baseline_financials or {},
            business_profile=business_profile,
        )
        
        # Step 4: Assemble final response
        response = {
            "query": query,
            "scenario_type": scenario_type,
            "assumptions": assumptions,
            "used_priors": True,
            "baseline": financial_result.get("baseline", {}),
            "projected": financial_result.get("projected", {}),
            "kpis": financial_result.get("kpis", {}),
            "advisor": financial_result.get("advisor", {}),
            "visuals": financial_result.get("visuals", []),
            "sources": sources,
            "explain_math": financial_result.get("explain_math"),
            "why_it_matters": financial_result.get("why_it_matters"),
        }
        
        return response
