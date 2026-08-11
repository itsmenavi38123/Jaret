import json
from datetime import datetime, timedelta
from typing import Any, Dict, List
from app.db import get_collection
from app.services.claude_service import claude_service
from app.services.customer_memory_service import CustomerMemoryService
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.services.quickbooks_token_service import quickbooks_token_service
from app.utils.memory_factory import MemoryFactory

class ForecastAccuracyService:
    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def evaluate_forecasts(self, user_id: str) -> int:
        """
        Evaluate past demand forecasts against actual sales data.
        Writes accuracy evaluation memories back to the database.
        """
        # Fetch QB actuals for the last 90 days to check against recent forecasts
        tokens = await quickbooks_token_service.get_tokens_by_user(user_id)
        active_tokens = [t for t in tokens if t.is_active]
        if not active_tokens:
            print(f"[Accuracy] User {user_id} has no active QuickBooks connection. Skipping.")
            return 0

        today = datetime.utcnow().date()
        start_date = today - timedelta(days=90)
        
        try:
            actual_sales = await quickbooks_financial_service.get_historical_sales(
                user_id=user_id,
                start_date=start_date,
                end_date=today,
                granularity="monthly"
            )
        except Exception as e:
            print(f"[Accuracy] Failed to fetch actual sales for user {user_id}: {e}")
            return 0

        if not actual_sales:
            print(f"[Accuracy] No actual sales data returned for user {user_id}. Skipping.")
            return 0

        # Fetch past forecast memories
        # These are outcome memories with tags containing "demand_forecast"
        past_forecasts = await self.memory_service.collection.find({
            "user_id": user_id,
            "observation_type": "outcome",
            "tags": {"$in": ["demand_forecast", "forecast"]},
            "outdated": {"$ne": True}
        }).sort("created_at", -1).to_list(length=10)

        if not past_forecasts:
            print(f"[Accuracy] No past forecast memories found for user {user_id}. Skipping.")
            return 0

        # Build Claude prompt to match forecasts with actuals
        system_prompt = """You are the LightSignal Forecast Accuracy Evaluator.
Your job is to compare past demand forecasts against actual revenue results and produce structured accuracy memories.

You will be given:
1. Past forecast memories (which include expected predictions, windows, and assumptions).
2. Trailing actual revenue records from QuickBooks.

Compare the forecast windows and predicted expected values against actual performance for the corresponding timeframes.
Note: Forecasts may use units or check sizes. Try to compute the percentage difference.
If the actual sales data covers a predicted window and allows evaluation:
- Calculate the percentage variance: |actual - predicted| / actual.
- Write a clear, advisor-grade trust-earning description of the accuracy (e.g. "Your last monthly forecast landed within 8% of actual — safe to commit on scheduling.").
- Author concrete, actionable "lean guidance" (e.g. "Safe to commit the weekend scheduling and produce order on this.").
- Assign an honest confidence score based on the variance.

Return STRICT JSON only. If no past forecasts can be evaluated with the current actuals, return an empty array.

Required output format:
{
  "accuracy_evaluations": [
    {
      "text": "Your last monthly forecast landed within 8% of actual...",
      "lean_guidance": "Safe to commit on this...",
      "confidence": 85,
      "forecast_memory_id": "ID of evaluated memory"
    }
  ]
}
"""

        user_content = {
            "past_forecasts": [
                {
                    "id": str(f["_id"]),
                    "created_at": f["created_at"].isoformat() if isinstance(f["created_at"], datetime) else str(f["created_at"]),
                    "content": f["content"],
                    "supporting_data": f.get("supporting_data", {})
                }
                for f in past_forecasts
            ],
            "actual_sales": actual_sales
        }

        try:
            result = await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=0.2,
                max_tokens=2000
            )
        except Exception as e:
            print(f"[Accuracy] Claude evaluation completion failed: {e}")
            return 0

        evaluations = result.get("accuracy_evaluations", [])
        if not isinstance(evaluations, list):
            return 0

        created_count = 0
        for ev in evaluations:
            text = ev.get("text")
            lean_guidance = ev.get("lean_guidance")
            confidence = ev.get("confidence", 80)
            forecast_id = ev.get("forecast_memory_id")

            if not text or not lean_guidance:
                continue

            # Create accuracy memory
            memory = MemoryFactory.create_memory(
                user_id=user_id,
                observation_type="outcome",
                content=text,
                agent_name="accuracy_evaluator",
                session_id="forecast_scoring",
                confidence="high" if confidence >= 85 else "medium",
                tags=["accuracy", "forecast_accuracy"],
                path=f"/memories/customer_{user_id}/accuracy/{forecast_id or 'eval'}.json",
                supporting_data={
                    "lean_guidance": lean_guidance,
                    "confidence_score": confidence,
                    "evaluated_forecast_memory_id": forecast_id
                }
            )
            memory.authority = "dreaming_pass"

            await self.memory_service.create_memory(memory)
            created_count += 1

            # Mark the evaluated forecast memory's outdated field to avoid re-evaluating it repeatedly
            if forecast_id:
                try:
                    from bson import ObjectId
                    await self.memory_service.collection.update_one(
                        {"_id": ObjectId(forecast_id)},
                        {"$set": {"outdated": True}}
                    )
                except Exception as ex:
                    print(f"[Accuracy] Failed to mark forecast memory {forecast_id} as evaluated/outdated: {ex}")

        return created_count

forecast_accuracy_service = ForecastAccuracyService()
