# backend/app/services/ai_insights_service.py
"""
AI Insights Service
Generates top 3 insights using Canonical Financial Analyst V6 (DASHBOARD MODE / INSIGHTS MODE).
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json
from app.services.claude_service import claude_service
from app.services.financial_overview_drawer_prompt import get_financial_analyst_prompt
from app.services.finance_analyst_service import FinanceAnalystService
from app.services.research_scout_service import ResearchScoutService


class AIInsightsService:
    """
    Service for generating AI-powered financial insights.
    Uses three agents: Orchestrator, Finance Analyst, Research Scout.
    """
    
    def __init__(self):
        self.finance_analyst = FinanceAnalystService()
        self.research_scout = ResearchScoutService()
    
    async def get_latest_insights(
        self,
        user_id: str,
        financial_data: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]] = None,
        classifier_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate top 3 AI insights: strength, issue, opportunity using Canonical FA V6.
        
        Args:
            user_id: User ID
            financial_data: Current financial KPIs and metrics
            business_profile: Business profile data
            classifier_output: Business profile classifier output
        
        Returns:
            Dict with insights array and metadata
        """
        system_prompt = get_financial_analyst_prompt()
        
        try:
            dashboard_result = await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content={
                    "request": "Generate dashboard analysis. Output ONLY valid JSON.",
                    "context": {
                        "financial_data": financial_data,
                        "business_profile": business_profile,
                    },
                    "classifier_output": classifier_output,
                },
                temperature=0.2,
                max_tokens=4000,
            )
            
            # Map canonical FA V6 dashboard output to insights schema
            insights = []
            
            # 1. Strength (from positive alerts or opportunities)
            positive_alerts = [a for a in dashboard_result.get("alerts", []) if a.get("type") == "positive"]
            if positive_alerts:
                top_pos = positive_alerts[0]
                insights.append({
                    "type": "strength",
                    "title": "Positive Performance",
                    "description": top_pos.get("message", "Key metrics are on track."),
                    "impact": "high" if top_pos.get("severity") == "above_average" else "medium",
                    "source": "Finance Analyst",
                    "action": "Maintain current operational momentum."
                })
            elif dashboard_result.get("what_changed"):
                insights.append({
                    "type": "strength",
                    "title": "Period Movement",
                    "description": dashboard_result["what_changed"][0],
                    "impact": "medium",
                    "source": "Finance Analyst",
                    "action": "Monitor trend continuation."
                })
            else:
                insights.append({
                    "type": "strength",
                    "title": "Financial Stability",
                    "description": dashboard_result.get("summary", "Business operations are stable."),
                    "impact": "medium",
                    "source": "Finance Analyst",
                    "action": "Continue tracking key performance indicators."
                })
                
            # 2. Issue (from critical/warning alerts or insight_pairs)
            risk_alerts = [a for a in dashboard_result.get("alerts", []) if a.get("type") in ("risk", "warning")]
            insight_pairs = dashboard_result.get("insight_pairs", [])
            if insight_pairs:
                top_pair = insight_pairs[0]
                insights.append({
                    "type": "issue",
                    "title": top_pair.get("head", "Operational Attention Needed") if isinstance(top_pair, dict) else "Operational Issue",
                    "description": top_pair.get("problem", "Identified risk in financial workflow.") if isinstance(top_pair, dict) else str(top_pair),
                    "impact": "high",
                    "source": "Finance Analyst",
                    "action": top_pair.get("solution", "Review and take recommended action.") if isinstance(top_pair, dict) else "Address root cause."
                })
            elif risk_alerts:
                top_risk = risk_alerts[0]
                insights.append({
                    "type": "issue",
                    "title": "Risk Alert",
                    "description": top_risk.get("message", "Attention required on key metric."),
                    "impact": "high" if top_risk.get("severity") == "critical" else "medium",
                    "source": "Finance Analyst",
                    "action": "Investigate underlying driver."
                })
            else:
                insights.append({
                    "type": "issue",
                    "title": "Cost & Expense Monitoring",
                    "description": "Operating expenses require regular monitoring to preserve runway.",
                    "impact": "medium",
                    "source": "Finance Analyst",
                    "action": "Audit monthly expenses and identify optimization opportunities."
                })
                
            # 3. Opportunity
            opportunities = dashboard_result.get("opportunities", [])
            if opportunities:
                top_opp = opportunities[0]
                if isinstance(top_opp, dict):
                    opp_title = top_opp.get("head", "Growth Lever")
                    opp_desc = top_opp.get("body", "Growth opportunity identified.")
                else:
                    opp_title = "Growth Lever"
                    opp_desc = str(top_opp)
                insights.append({
                    "type": "opportunity",
                    "title": opp_title[:40],
                    "description": opp_desc,
                    "impact": "high",
                    "source": "Finance Analyst",
                    "action": "Execute strategic growth initiative."
                })
            else:
                insights.append({
                    "type": "opportunity",
                    "title": "Market Expansion Potential",
                    "description": "Explore regional market trends and external opportunities.",
                    "impact": "medium",
                    "source": "Research Scout",
                    "action": "Review external opportunities in Opportunities tab."
                })
            
            return {
                "insights": insights[:3],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            print(f"AI insights generation failed: {e}")
            return self._generate_fallback_insights(financial_data)
    
    def _generate_fallback_insights(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate basic rule-based insights if AI fails.
        """
        insights = []
        kpis = financial_data.get("kpis", {})
        
        # Strength: Look for positive revenue growth
        revenue_mtd = kpis.get("revenue_mtd", 0)
        if revenue_mtd > 0:
            insights.append({
                "type": "strength",
                "title": "Positive Revenue Performance",
                "description": f"Current month revenue of ${revenue_mtd:,.2f} shows business activity.",
                "impact": "medium",
                "source": "Finance Analyst",
                "action": "Continue monitoring revenue trends and customer acquisition"
            })
        else:
            insights.append({
                "type": "strength",
                "title": "Operational Baseline",
                "description": "Baseline operations established.",
                "impact": "medium",
                "source": "Finance Analyst",
                "action": "Track incoming revenue streams"
            })
        
        # Issue: Check runway
        runway = kpis.get("runway_months")
        if runway and runway < 6:
            insights.append({
                "type": "issue",
                "title": "Limited Cash Runway",
                "description": f"Current runway of {runway:.1f} months requires immediate attention.",
                "impact": "high",
                "source": "Finance Analyst",
                "action": "Review expenses and explore financing options"
            })
        else:
            insights.append({
                "type": "issue",
                "title": "Monitor Operating Expenses",
                "description": "Regular expense review ensures optimal cost management.",
                "impact": "medium",
                "source": "Finance Analyst",
                "action": "Conduct monthly expense analysis and identify optimization opportunities"
            })
        
        # Opportunity: Generic
        insights.append({
            "type": "opportunity",
            "title": "Market Expansion Potential",
            "description": "Explore regional market trends and competitive positioning.",
            "impact": "medium",
            "source": "Research Scout",
            "action": "Research local market demand and competitor landscape"
        })
        
        return {
            "insights": insights[:3],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
ai_insights_service = AIInsightsService()
