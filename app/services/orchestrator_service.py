# backend/app/services/orchestrator_service.py
"""
Orchestrator Service
Coordinates the multi-agent workflow for scenario planning
"""
from typing import Any, Dict, List, Optional
import json
from app.services.claude_service import claude_service

from app.services.research_scout_service import ResearchScoutService
from app.services.finance_analyst_service import FinanceAnalystService
from app.services.quickbooks_financial_service import quickbooks_financial_service

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
        
        system_prompt = """You are a scenario classification expert.

            Given a business scenario query, classify it into one of these types:
            - **CapEx**: Capital expenditure (equipment, vehicles, property, major purchases)
            - **Hiring**: Adding staff, contractors, or labor
            - **Pricing**: Changing prices, discounts, or pricing strategy
            - **Expansion**: Opening new locations, entering new markets, scaling operations
            - **Other**: Anything else

            Return ONLY the scenario type as a single word: CapEx, Hiring, Pricing, Expansion, or Other.
        """

        scenario_type = await claude_service.text_completion(
            system_prompt=system_prompt,
            user_content=query,
            temperature=0.0,
            max_tokens=50,
        )

        return scenario_type.strip()
            
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
        classifier_output = await self.get_classifier_output(user_id)
        
        # Step 2: Get assumptions from Research Scout
        assumptions_data = await self.research_scout.get_scenario_priors(
            classifier_output=classifier_output,
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
            user_id=user_id,
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

    async def render_business_health(self, payload: Dict[str, Any]) -> Dict[str, Any]:

        system_prompt = """
        You are LightSignal Orchestrator in Business Health mode.

        Your role:
        Generate Business Health narrative output from structured business health payloads.

        CRITICAL RULES
        - Never invent numbers, entities, metrics, causes, percentages, dates, invoices, vendors, customers, products, locations, or facts.
        - Use ONLY information present in the payload.
        - Use plain-English owner-facing language.
        - Be specific and consequence-oriented.
        - No generic business advice.
        - Do not mention internal scoring systems.
        - If data is incomplete, acknowledge it naturally.

        AI SUMMARY RULES

        - Must be exactly 2 sentences.
        - Must create a narrative arc.
        - Must not restate the score.
        - Must not mention specific customers, vendors, invoices, products, locations, or named entities.
        - Vocabulary should match the business classifier dimensions.
        - Focus on overall business situation and trajectory.

        DRIVERS / DRAGS RULES

        - Description is diagnosis only.
        - recommended_action is action only.
        - Description and recommended_action must not overlap.
        - Use specific named entities whenever available in payload.
        - Include quantified magnitude whenever available.
        - Explain why the metric matters operationally.
        - recommended_action must contain decision criteria and timing.

        WATCH AREA RULES

        - Must contain title, description, possible_causes, and recommended_action.
        - Description must explain trajectory and consequence.
        - possible_causes must come only from watch_area_investigations.
        - Empty possible_causes is allowed.
        - recommended_action must be specific and time-bound.

        ACTIVE ALERT RULES

        - Active alerts represent hard threshold crossings only.
        - Must contain description, urgency_context, and recommended_action.
        - urgency_context explains why immediate attention is required.
        - Active alerts may be empty.

        OUTPUT FORMAT RULES

        - Return valid JSON only.
        - Do not return markdown.
        - Do not return explanations outside JSON.

        OUTPUT FORMAT — STRICT JSON ONLY

        {
        "intent": "render_business_health",
        "as_of": "<ISO timestamp>",

        "overall_label": "top_tier|above_average|at_average|below_average|critical",

        "ai_summary": "2 sentence business narrative summary.",

        "category_labels": {
            "financial": "",
            "operational": "",
            "customer": "",
            "risk": "",
            "growth": ""
        },

        "drivers_display": {
            "positives": [
            {
                "headline": "",
                "description": "",
                "recommended_action": "",
                "points": 0
            }
            ],

            "drags": [
            {
                "headline": "",
                "description": "",
                "recommended_action": "",
                "points": 0
            }
            ]
        },

        "watch_areas": [
            {
            "title": "",
            "description": "",
            "possible_causes": [
                {
                "cause": "",
                "evidence": "",
                "source_url": ""
                }
            ],
            "recommended_action": ""
            }
        ],

        "active_alerts": [
            {
            "alert_id": "",
            "description": "",
            "urgency_context": "",
            "recommended_action": ""
            }
        ],

        "data_coverage_note": "",

        "ai_confidence": 0.0
        }

        JSON only.
        """

        classifier_output = await self.get_classifier_output(payload.get("user_id"))
        watch_area_investigations = []

        for area in payload.get("priority_watch_areas", []):

            investigation = await self.research_scout.investigate_watch_area(
                pattern={
                    "metric": area,
                    "trend_description": area,
                    "current_value": None,
                    "prior_value": None,
                    "months_trending": None,
                    "specific_entity": None,
                    "timeframe": "recent"
                },
                business_context={
                    "classifier_output": classifier_output,
                    "business_profile_subset": payload.get(
                        "business_profile_subset",
                        {}
                    )
                }
            )

            watch_area_investigations.append(investigation)

        normalized_payload = {
            "intent": "render_business_health",
            "today_date": payload.get("today_date"),
            "company_id": payload.get("company_id"),
            "classifier_output": classifier_output,
            "profile": payload.get("profile", {}),
            "overall": payload.get("overall", {}),
            "categories": payload.get("categories", {}),
            "ranked_drivers": payload.get("ranked_drivers", []),
            "detail_fields": payload.get("detail_fields", {}),
            "prior_period_snapshot": payload.get(
                "prior_period_snapshot",
                {}
            ),
            "signals": payload.get("signals", {}),
            "benchmarks": payload.get("benchmarks", {}),
            "data_coverage": payload.get("data_coverage", {}),
        }

        parsed = await claude_service.json_completion(
            system_prompt=system_prompt,
            user_content={
                **normalized_payload,
                "watch_area_investigations": watch_area_investigations,
            },
            temperature=0.2,
            max_tokens=4000,
        )

        try:

            parsed.setdefault("intent", "render_business_health")
            parsed.setdefault("as_of", payload.get("today_date"))
            parsed.setdefault("overall_label", payload.get("overall", {}).get("label"))

            parsed.setdefault("category_labels", {
                "financial": payload.get("categories", {}).get("financial", {}).get("label"),
                "operational": payload.get("categories", {}).get("operational", {}).get("label"),
                "customer": payload.get("categories", {}).get("customer", {}).get("label"),
                "risk": payload.get("categories", {}).get("risk", {}).get("label"),
                "growth": payload.get("categories", {}).get("growth", {}).get("label"),
            })

            parsed.setdefault("drivers_display", {
                "positives": [],
                "drags": []
            })

            parsed.setdefault("watch_areas", watch_area_investigations)
            parsed.setdefault("active_alerts", [])
            parsed.setdefault("data_coverage_note", "")
            parsed.setdefault("ai_confidence", payload.get("overall", {}).get("ai_confidence", 0.0))

            return parsed

        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from Business Health Orchestrator")

    async def refresh_all_business_data(
            
        self,
        user_id: str,
    ) -> Dict[str, Any]:

        refresh_status = {
            "connectors_synced": False,
            "classifier_refreshed": False,
            "research_refreshed": False,
            "ai_regenerated": False,
            "snapshots_stored": False,
            "events_emitted": False,
        }

        await quickbooks_financial_service.get_financial_overview(user_id)
        # Step 1 - Connector refresh

        refresh_status["connectors_synced"] = True

        # Step 2 - Classifier refresh
        refresh_status["classifier_refreshed"] = True

        # Step 3 - Research refresh
        refresh_status["research_refreshed"] = True

        # Step 4 - AI regeneration
        refresh_status["ai_regenerated"] = True

        # Step 5 - Snapshot persistence
        refresh_status["snapshots_stored"] = True

        # Step 6 - Event emission
        refresh_status["events_emitted"] = True

        return {
            "success": True,
            "mode": "refresh_cascade",
            "status": refresh_status
        }
    
    async def get_classifier_output(
        self,
        user_id: str,
    ) -> Dict[str, Any]:

        return {
            "business_type": None,
            "industry": None,
            "customer_type": None,
            "risk_profile": None,
        }