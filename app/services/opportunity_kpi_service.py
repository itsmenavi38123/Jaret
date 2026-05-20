from datetime import datetime, timedelta
from typing import Dict, Any


class OpportunityKPIService:

    async def build_overview_kpis(
        self,
        user_id: str,
        opportunities_collection,
        outcomes_collection,
    ):

        now = datetime.utcnow()

        opportunities = await opportunities_collection.find({
            "user_id": user_id,
        }).to_list(length=1000)

        outcomes = await outcomes_collection.find({
            "user_id": user_id,
        }).to_list(length=1000)

        active_opportunities = []

        for opportunity in opportunities:

            if not self.is_active_opportunity(opportunity, now):
                continue

            if not self.matches_profile_conditions(opportunity, now):
                continue

            active_opportunities.append(opportunity)

        new_this_week = [
            opp for opp in active_opportunities
            if opp.get("ingested_at")
        ]

        active_count = len(active_opportunities)

        total_potential_values = [
            opp.get("estimated_revenue")
            for opp in active_opportunities
            if opp.get("estimated_revenue") is not None
        ]

        total_potential_value = (
            sum(total_potential_values)
            if total_potential_values
            else None
        )

        return {
            "active_opportunities": {
                "count": active_count,
                "new_this_week": len(new_this_week),
            },
            "total_potential_value": total_potential_value,
            "avg_fit_score": {},
            "event_readiness_index": {},
            "historical_roi": {},
        }

    def is_active_opportunity(
        self,
        opportunity: Dict[str, Any],
        now: datetime,
    ) -> bool:

        expires_at = opportunity.get("expires_at")

        if not expires_at:
            return False

        try:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except:
            return False

        return expires_dt >= now

    def matches_profile_conditions(
        self,
        opportunity: Dict[str, Any],
        now: datetime,
    ) -> bool:

        opportunity_type = opportunity.get("type", "").lower().strip()
        allowed_types = ["event", "grant", "rfp", "festival", "market", "expo", "conference", "partnership", "vendor", "competition", "award", "incentive", "program", "promotion"]
        if opportunity_type not in allowed_types:
            return False
        drive_time_minutes = opportunity.get("geo", {}).get("drive_time_minutes")
        if drive_time_minutes is not None and drive_time_minutes > 180:
            return False

        if opportunity_type == "event":
            start_date = opportunity.get("start_date")
            if not start_date:
                return False
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except:
                return False
            if start_dt > (now + timedelta(days=120)):
                return False

        else:

            target_date = opportunity.get("deadline") or opportunity.get("start_date")
            if target_date:
                try:
                    target_dt = datetime.fromisoformat(target_date.replace("Z", "+00:00"))
                except:
                    return False
                if target_dt > (now + timedelta(days=180)):
                    return False

        return True


opportunity_kpi_service = OpportunityKPIService()