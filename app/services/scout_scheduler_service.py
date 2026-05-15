import asyncio
from datetime import datetime

from app.db import get_collection
from app.services.research_scout_service import ResearchScoutService
from app.routes.ai_opportunities import process_scout_output


class ScoutSchedulerService:

    def __init__(self):
        self.research_scout = ResearchScoutService()

    async def run_daily_scout_pipeline(self):

        business_profiles = get_collection("business_profiles")
        opportunities_profiles = get_collection("opportunities_profiles")
        quickbooks_tokens = get_collection("quickbooks_tokens")
        scout_runs = get_collection("scout_runs")
        users = get_collection("users")

        businesses = await business_profiles.find({}).to_list(length=None)

        for business_profile in businesses:

            user_id = business_profile.get("user_id")

            onboarding = business_profile.get(
                "onboarding_data",
                {},
            )

            geo = onboarding.get("geo", {})

            city = geo.get("city")
            state = geo.get("state")

            if not city or not state:
                continue

            user = await users.find_one(
                {"_id": user_id}
            )

            if user and user.get("is_deactivated"):
                continue

            qb_connected = await quickbooks_tokens.find_one(
                {
                    "user_id": user_id,
                    "is_active": True,
                }
            )

            if not qb_connected:
                continue

            today_start = datetime.utcnow().replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

            existing_run = await scout_runs.find_one(
                {
                    "business_id": user_id,
                    "run_type": "scheduled",
                    "status": "completed",
                    "started_at": {
                        "$gte": today_start,
                    },
                }
            )

            if existing_run:
                continue

            opportunities_profile = await opportunities_profiles.find_one(
                {"user_id": user_id}
            )

            try:

                result = await self.research_scout.search_opportunities(
                    query="daily business opportunity discovery",
                    user_id=user_id,
                    business_profile=business_profile,
                    opportunities_profile=opportunities_profile,
                    mode="live",
                    run_type="scheduled",
                )

                if (
                    result.get("opportunities")
                    and result["opportunities"].get("cards")
                ):
                    result["opportunities"]["cards"] = (
                        result["opportunities"]["cards"][:12]
                    )

                pipeline_stats = await process_scout_output(
                    user_id=user_id,
                    result=result,
                )

                await scout_runs.insert_one(
                    {
                        "business_id": user_id,
                        "run_type": "scheduled",
                        "started_at": datetime.utcnow(),
                        "completed_at": datetime.utcnow(),
                        "status": "completed",
                        "cards_returned": len(
                            result.get(
                                "opportunities",
                                {},
                            ).get(
                                "cards",
                                [],
                            )
                        ),
                        "dedup_skipped": pipeline_stats["dedup_skipped"],
                        "tracked_skipped": pipeline_stats["tracked_skipped"],
                        "small_market_flag": False,
                        "queries_run": [
                            "daily business opportunity discovery"
                        ],
                    }
                )

            except Exception as e:

                await scout_runs.insert_one(
                    {
                        "business_id": user_id,
                        "run_type": "scheduled",
                        "started_at": datetime.utcnow(),
                        "status": "failed",
                        "error_message": str(e),
                    }
                )

            await asyncio.sleep(5)