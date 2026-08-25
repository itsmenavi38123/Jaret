from app.models.financial_overview_insights import (
    FinancialOverviewInsights,
    FinancialOverviewInsightItem,
    ProfitabilityBanner,
)
from app.services.finance_analyst_service import (
    finance_analyst_service,
)
from app.services.financial_overview_actions_service import (
    financial_overview_actions_service,
)


class FinancialOverviewInsightsService:

    async def generate_insights(
        self,
        user_id: str,
        financial_overview: dict,
        business_health: dict,
        classifier_output: dict | None = None,
    ):
        from app.db import get_collection
        users_col = get_collection("users")
        user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
        
        if user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", "")):
            login_label = user_doc.get("login_label") or user_doc.get("username")
            if not login_label and user_doc.get("email"):
                login_label = user_doc.get("email").split("@")[0]
            
            from app.demo_data import get_demo_payload
            demo_payload = get_demo_payload(login_label or "demo-restaurant")
            if demo_payload and "insights_mode" in demo_payload:
                return demo_payload["insights_mode"]

        try:
            response = await finance_analyst_service.generate_financial_overview_insights(
                financial_overview=financial_overview,
                business_health=business_health,
                classifier_output=classifier_output,
            )
            if response and isinstance(response, dict) and "insights" in response:
                response["insights"] = await financial_overview_actions_service.apply_user_actions_to_insights(
                    user_id=user_id,
                    insights=response["insights"],
                )
            return response
        except Exception as e:
            print(f"[WARN] Failed to generate AI financial_overview_insights: {e}")
            return None


financial_overview_insights_service = (
    FinancialOverviewInsightsService()
)