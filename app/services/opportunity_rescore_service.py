from datetime import datetime
from typing import Dict, Any
from app.db import get_collection
from app.services.scoring_service import scoring_service
from app.services.internal_event_bus import internal_event_bus

class OpportunityRescoreService:

    def __init__(self):
        self.opportunities = get_collection("opportunities")

    async def rescore_opportunity(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
        trigger: str,
    ) -> Dict[str, Any]:

        scoring_result = await scoring_service.rescore_opportunity(
            opportunity=opportunity,
            business_context=business_context,
            trigger=trigger,
        )

        updated_scoring_data = {
            **opportunity.get("scoring_data", {}),
            "score_history": scoring_result["score_history"],
            "original_preliminary_fit_score": opportunity.get(
                "scoring_data",
                {},
            ).get(
                "original_preliminary_fit_score",
                opportunity.get("fit_score", 0),
            ),
        }

        update_data = {
            "match_score": scoring_result["match_score"],
            "readiness_score": scoring_result["readiness_score"],
            "portfolio_adjusted_readiness": scoring_result.get("portfolio_adjusted_readiness"),
            "event_readiness_score": scoring_result["event_readiness_score"],
            "last_scored_at": scoring_result["last_scored_at"],
            "event_readiness_label": scoring_result.get("event_readiness_label"),
            "expected_roi_mult": scoring_result.get("expected_roi_mult"),
            "expected_roi_display": scoring_result.get("expected_roi_display"),
            "why_reason_codes": scoring_result.get("why_reason_codes", []),
            "scoring_data": updated_scoring_data,

            "verification_data": {
                **opportunity.get("verification_data", {}),
                "data_trust_indicator": scoring_result["data_trust_indicator"],
            },

            "updated_at": datetime.utcnow(),
        }

        await self.opportunities.update_one(
            {"_id": opportunity["_id"]},
            {"$set": update_data},
        )

        return update_data

    async def daily_rescore_active_opportunities(self):

        active_opportunities = await self.opportunities.find(
            {
                "$or": [
                    {
                        "deadline": {
                            "$gte": datetime.utcnow(),
                        }
                    },
                    {
                        "date": {
                            "$gte": datetime.utcnow().strftime("%Y-%m-%d"),
                        }
                    },
                ],

                "status_user": {
                    "$nin": [
                        "selected",
                    ]
                }
            }
        ).to_list(length=None)

        rescore_count = 0

        for opportunity in active_opportunities:

            business_context = {
                "business_classifications": opportunity.get("business_classifications", []),
                "cash_balance": opportunity.get("cash_balance", 0),
                "outstanding_ar": opportunity.get("outstanding_ar", []),
                "runway_trend": opportunity.get("runway_trend", "stable"),
                "demand_strain_next_30d": opportunity.get("demand_strain_next_30d"),
                "demand_strain_next_60d": opportunity.get("demand_strain_next_60d"),
                "demand_strain_next_90d": opportunity.get("demand_strain_next_90d"),
                "latest_demand_forecast": opportunity.get("latest_demand_forecast"),
                "permits_and_licenses": opportunity.get("permits_and_licenses", []),
            }

            await self.rescore_opportunity(
                opportunity=opportunity,
                business_context=business_context,
                trigger="daily_rescore",
            )

            rescore_count += 1

        return {
            "rescored": rescore_count,
        }

    async def rescore_by_profile_update(
        self,
        business_id: str,
    ) -> Dict[str, Any]:

        active_opportunities = await self.opportunities.find(
            {
                "user_id": business_id,

                "$or": [
                    {
                        "deadline": {
                            "$gte": datetime.utcnow(),
                        }
                    },
                    {
                        "date": {
                            "$gte": datetime.utcnow().strftime("%Y-%m-%d"),
                        }
                    },
                ],

                "status_user": {
                    "$nin": [
                        "selected",
                    ]
                }
            }
        ).to_list(length=None)

        rescore_count = 0

        for opportunity in active_opportunities:

            business_context = {
                "business_classifications": opportunity.get("business_classifications", []),
                "cash_balance": opportunity.get("cash_balance", 0),
                "outstanding_ar": opportunity.get("outstanding_ar", []),
                "runway_trend": opportunity.get("runway_trend", "stable"),
                "demand_strain_next_30d": opportunity.get("demand_strain_next_30d"),
                "demand_strain_next_60d": opportunity.get("demand_strain_next_60d"),
                "demand_strain_next_90d": opportunity.get("demand_strain_next_90d"),
                "latest_demand_forecast": opportunity.get("latest_demand_forecast"),
                "permits_and_licenses": opportunity.get("permits_and_licenses", []),
            }

            await self.rescore_opportunity(
                opportunity=opportunity,
                business_context=business_context,
                trigger="profile_update",
            )

            rescore_count += 1

        return {
            "rescored": rescore_count,
        }

    async def rescore_by_cash_update(
        self,
        business_id: str,
    ) -> Dict[str, Any]:

        active_opportunities = await self.opportunities.find(
            {
                "user_id": business_id,

                "$or": [
                    {
                        "deadline": {
                            "$gte": datetime.utcnow(),
                        }
                    },
                    {
                        "date": {
                            "$gte": datetime.utcnow().strftime("%Y-%m-%d"),
                        }
                    },
                ],

                "status_user": {
                    "$nin": [
                        "selected",
                    ]
                }
            }
        ).to_list(length=None)

        rescore_count = 0

        for opportunity in active_opportunities:

            business_context = {
                "business_classifications": opportunity.get("business_classifications", []),
                "cash_balance": opportunity.get("cash_balance", 0),
                "outstanding_ar": opportunity.get("outstanding_ar", []),
                "runway_trend": opportunity.get("runway_trend", "stable"),
                "demand_strain_next_30d": opportunity.get("demand_strain_next_30d"),
                "demand_strain_next_60d": opportunity.get("demand_strain_next_60d"),
                "demand_strain_next_90d": opportunity.get("demand_strain_next_90d"),
                "latest_demand_forecast": opportunity.get("latest_demand_forecast"),
                "permits_and_licenses": opportunity.get("permits_and_licenses", []),
            }

            await self.rescore_opportunity(
                opportunity=opportunity,
                business_context=business_context,
                trigger="cash_update",
            )

            rescore_count += 1

        return {
            "rescored": rescore_count,
        }

    async def rescore_by_weather_update(
        self,
        business_id: str,
    ) -> Dict[str, Any]:

        active_opportunities = await self.opportunities.find(
            {
                "user_id": business_id,

                "$or": [
                    {
                        "deadline": {
                            "$gte": datetime.utcnow(),
                        }
                    },
                    {
                        "date": {
                            "$gte": datetime.utcnow().strftime("%Y-%m-%d"),
                        }
                    },
                ],

                "status_user": {
                    "$nin": [
                        "selected",
                    ]
                }
            }
        ).to_list(length=None)

        rescore_count = 0

        for opportunity in active_opportunities:

            business_context = {
                "business_classifications": opportunity.get(
                    "business_classifications",
                    [],
                ),
                "cash_balance": opportunity.get("cash_balance", 0),
                "outstanding_ar": opportunity.get("outstanding_ar", []),
                "runway_trend": opportunity.get("runway_trend", "stable"),
                "demand_strain_next_30d": opportunity.get("demand_strain_next_30d"),
                "demand_strain_next_60d": opportunity.get("demand_strain_next_60d"),
                "demand_strain_next_90d": opportunity.get("demand_strain_next_90d"),
                "latest_demand_forecast": opportunity.get("latest_demand_forecast"),
                "permits_and_licenses": opportunity.get("permits_and_licenses", []),
            }

            await self.rescore_opportunity(
                opportunity=opportunity,
                business_context=business_context,
                trigger="weather_update",
            )

            rescore_count += 1

        return {
            "rescored": rescore_count,
        }

    async def rescore_by_demand_update(
        self,
        business_id: str,
    ) -> Dict[str, Any]:

        active_opportunities = await self.opportunities.find(
            {
                "user_id": business_id,

                "$or": [
                    {
                        "deadline": {
                            "$gte": datetime.utcnow(),
                        }
                    },
                    {
                        "date": {
                            "$gte": datetime.utcnow().strftime("%Y-%m-%d"),
                        }
                    },
                ],

                "status_user": {
                    "$nin": [
                        "selected",
                    ]
                }
            }
        ).to_list(length=None)

        rescore_count = 0

        for opportunity in active_opportunities:

            business_context = {
                "business_classifications": opportunity.get(
                    "business_classifications",
                    [],
                ),
                "cash_balance": opportunity.get("cash_balance", 0),
                "outstanding_ar": opportunity.get("outstanding_ar", []),
                "runway_trend": opportunity.get("runway_trend", "stable"),
                "demand_strain_next_30d": opportunity.get("demand_strain_next_30d"),
                "demand_strain_next_60d": opportunity.get("demand_strain_next_60d"),
                "demand_strain_next_90d": opportunity.get("demand_strain_next_90d"),
                "latest_demand_forecast": opportunity.get("latest_demand_forecast"),
                "permits_and_licenses": opportunity.get("permits_and_licenses", []),
            }

            await self.rescore_opportunity(
                opportunity=opportunity,
                business_context=business_context,
                trigger="demand_update",
            )

            rescore_count += 1

        return {
            "rescored": rescore_count,
        }

    async def rescore_by_portfolio_change(
        self,
        business_id: str,
    ) -> Dict[str, Any]:

        active_opportunities = await self.opportunities.find(
            {
                "user_id": business_id,

                "$or": [
                    {
                        "deadline": {
                            "$gte": datetime.utcnow(),
                        }
                    },
                    {
                        "date": {
                            "$gte": datetime.utcnow().strftime("%Y-%m-%d"),
                        }
                    },
                ],

                "status_user": {
                    "$nin": [
                        "selected",
                    ]
                }
            }
        ).to_list(length=None)

        rescore_count = 0

        for opportunity in active_opportunities:

            business_context = {
                "business_classifications": opportunity.get(
                    "business_classifications",
                    [],
                ),
                "cash_balance": opportunity.get("cash_balance", 0),
                "outstanding_ar": opportunity.get("outstanding_ar", []),
                "runway_trend": opportunity.get("runway_trend", "stable"),
                "demand_strain_next_30d": opportunity.get("demand_strain_next_30d"),
                "demand_strain_next_60d": opportunity.get("demand_strain_next_60d"),
                "demand_strain_next_90d": opportunity.get("demand_strain_next_90d"),
                "latest_demand_forecast": opportunity.get("latest_demand_forecast"),
                "permits_and_licenses": opportunity.get("permits_and_licenses", []),
            }

            await self.rescore_opportunity(
                opportunity=opportunity,
                business_context=business_context,
                trigger="portfolio_change",
            )

            rescore_count += 1

        return {
            "rescored": rescore_count,
        }
    
    async def handle_profile_classified_event(payload):

        business_id = payload.get("business_id")

        if not business_id:
            return

        await opportunity_rescore_service.rescore_by_profile_update(
            business_id=business_id
        )


    internal_event_bus.subscribe(
        "business.profile_classified",
        handle_profile_classified_event,
    )

opportunity_rescore_service = OpportunityRescoreService()