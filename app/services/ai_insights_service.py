# backend/app/services/ai_insights_service.py
"""
AI Insights Service
Generates top 3 insights using Orchestrator, Finance Analyst, and Research Scout
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json
import os
from openai import AsyncOpenAI

from app.services.finance_analyst_service import FinanceAnalystService
from app.services.research_scout_service import ResearchScoutService


class AIInsightsService:
    """
    Service for generating AI-powered financial insights.
    Uses three OpenAI agents: Orchestrator, Finance Analyst, Research Scout.
    """
    
    def __init__(self):
        self.finance_analyst = FinanceAnalystService()
        self.research_scout = ResearchScoutService()
    
    async def get_latest_insights(
        self,
        user_id: str,
        financial_data: Dict[str, Any],
        business_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate top 3 AI insights: strength, issue, opportunity.
        
        Args:
            user_id: User ID
            financial_data: Current financial KPIs and metrics
            business_profile: Business profile data
        
        Returns:
            Dict with insights array and metadata
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Extract industry and location from business profile
        industry = "Unknown"
        location = {"city": "", "state": ""}
        if business_profile and business_profile.get("onboarding_data"):
            onboarding = business_profile["onboarding_data"]
            industry = onboarding.get("industry", onboarding.get("business_type", "Unknown"))
            # Try to extract location if available
            if "location" in onboarding:
                location = onboarding["location"]
        
        # Build system prompt for Orchestrator (Insights mode)
        system_prompt = f"""You are LightSignal Orchestrator in Dashboard Insights mode.

Your mission: Generate exactly 3 actionable insights for the business dashboard:
1. One STRENGTH (what's working well)
2. One ISSUE (what needs attention)
3. One OPPORTUNITY (what to pursue)

🧰 CONTEXT

- **Industry**: {industry}
- **Location**: {location.get('city', '')}, {location.get('state', '')}
- **Financial Data**: {json.dumps(financial_data, default=str)}
- **Business Profile**: {json.dumps(business_profile, default=str) if business_profile else "None"}

📊 FINANCIAL METRICS AVAILABLE

You have access to:
- Revenue (MTD, QTD, YTD)
- Margins (Gross, Net, OpEx %)
- Cash position and runway
- Liquidity ratios (Current, Quick)
- Efficiency metrics (DSO, DPO, Inventory Turns)
- Cash flow and burn rate
- Prior period comparisons (deltas)

🎯 OUTPUT FORMAT — STRICT JSON ONLY

Return one object shaped as:

{{
  "insights": [
    {{
      "type": "strength",
      "title": "Short, punchy title (max 6 words)",
      "description": "One clear sentence explaining what's working and why it matters. Include specific numbers.",
      "impact": "high|medium|low",
      "source": "Finance Analyst|Research Scout|Orchestrator",
      "action": "One specific, actionable recommendation"
    }},
    {{
      "type": "issue",
      "title": "Short, punchy title (max 6 words)",
      "description": "One clear sentence explaining the problem and its impact. Include specific numbers.",
      "impact": "high|medium|low",
      "source": "Finance Analyst|Research Scout|Orchestrator",
      "action": "One specific, actionable recommendation"
    }},
    {{
      "type": "opportunity",
      "title": "Short, punchy title (max 6 words)",
      "description": "One clear sentence explaining the opportunity and potential impact. Include context.",
      "impact": "high|medium|low",
      "source": "Finance Analyst|Research Scout|Orchestrator",
      "action": "One specific, actionable recommendation"
    }}
  ]
}}

⚙️ INSIGHT GENERATION RULES

**STRENGTH** - Look for:
- Revenue growth vs prior period (>5% is notable)
- Margin improvements
- Strong liquidity ratios (Current >1.5, Quick >1.0)
- Positive cash flow trends
- Efficient working capital (low DSO, high inventory turns)
- Runway extending

**ISSUE** - Look for:
- Revenue decline or stagnation
- Margin compression (>2% drop)
- Low or declining cash position
- Runway shrinking (<6 months is critical)
- Poor liquidity (Current <1.0, Quick <0.5)
- Rising burn rate
- Inefficient working capital (high DSO, low turns)

**OPPORTUNITY** - Consider:
- Regional market trends (use Research Scout context)
- Underutilized capacity
- Pricing power (if margins are low but revenue is growing)
- Working capital optimization potential
- Seasonal patterns
- Industry benchmarks showing room for improvement

🧮 CALCULATION EXAMPLES

- Revenue delta: (Current - Prior) / Prior × 100
- Margin trend: Current Margin - Prior Margin
- Runway change: Current Runway - Prior Runway
- Burn rate trend: Current Burn - Prior Burn

✅ QUALITY RULES

- Use REAL numbers from the financial data provided
- Be specific: "Revenue up 15% vs last month" not "Revenue is growing"
- Make actions concrete: "Review top 3 supplier contracts" not "Reduce costs"
- Impact should reflect actual business significance
- Source should indicate which agent would provide this insight
- Keep titles short and scannable (max 6 words)
- Descriptions should be one clear sentence with numbers
- Actions should be immediately actionable

🚫 NEVER

- Invent numbers not in the data
- Give generic advice ("improve efficiency")
- Use vague language ("consider looking into")
- Exceed one sentence per description
- Provide more or fewer than 3 insights
- Duplicate insight types

JSON only (no Markdown, no prose outside fields).
"""
        
        # Call OpenAI Orchestrator
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate dashboard insights based on the financial data provided."}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON
        try:
            result = json.loads(content)
            insights = result.get("insights", [])
            
            # Validate we have exactly 3 insights
            if len(insights) != 3:
                raise ValueError(f"Expected 3 insights, got {len(insights)}")
            
            # Validate insight types
            types_found = {insight.get("type") for insight in insights}
            expected_types = {"strength", "issue", "opportunity"}
            if types_found != expected_types:
                raise ValueError(f"Expected types {expected_types}, got {types_found}")
            
            return {
                "insights": insights,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback to basic insights if AI fails
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
            # Generic issue
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
            "insights": insights,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
ai_insights_service = AIInsightsService()
