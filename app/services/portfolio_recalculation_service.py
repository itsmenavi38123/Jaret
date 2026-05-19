from datetime import datetime, timedelta
from typing import Dict, Any, List


class PortfolioRecalculationService:

    def build_opportunity_window(
        self,
        opportunity: Dict[str, Any],
    ):

        opportunity_type = (
            opportunity.get("type", "")
            .lower()
            .strip()
        )

        start_date = opportunity.get("start_date")
        end_date = opportunity.get("end_date")

        if opportunity_type in ["grant", "rfp"]:

            deadline = opportunity.get("deadline")

            if not deadline:
                return None, None

            deadline_dt = datetime.fromisoformat(deadline)

            return (
                deadline_dt - timedelta(days=7),
                deadline_dt,
            )

        if not start_date:
            return None, None

        start_dt = datetime.fromisoformat(start_date)

        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        else:
            end_dt = start_dt

        return start_dt, end_dt
    
    def windows_overlap(
        self,
        candidate_start,
        candidate_end,
        committed_start,
        committed_end,
    ) -> bool:

        if not all([
            candidate_start,
            candidate_end,
            committed_start,
            committed_end,
        ]):
            return False

        return (
            committed_start <= candidate_start <= committed_end
            or committed_start <= candidate_end <= committed_end
            or (
                candidate_start <= committed_start
                and candidate_end >= committed_end
            )
        )


    async def recalculate_portfolio_readiness(
        self,
        user_id: str,
        opportunities_collection,
    ):

        active_opportunities = await opportunities_collection.find({
            "user_id": user_id,
        }).to_list(length=500)

        committed = [
            opp for opp in active_opportunities
            if opp.get("status") in ["Tracked", "Selected"]
        ]

        for opportunity in active_opportunities:

            base_readiness = (
                opportunity.get("readiness_score")
                or 0
            )

            candidate_start, candidate_end = (
                self.build_opportunity_window(opportunity)
            )

            overlap_count = 0

            for committed_opp in committed:

                if str(committed_opp.get("_id")) == str(opportunity.get("_id")):
                    continue

                committed_start, committed_end = (
                    self.build_opportunity_window(committed_opp)
                )

                overlaps = self.windows_overlap(
                    candidate_start,
                    candidate_end,
                    committed_start,
                    committed_end,
                )

                if overlaps:
                    overlap_count += 1

            deduction = overlap_count * 5

            adjusted = max(
                base_readiness - deduction,
                0,
            )

            await opportunities_collection.update_one(
                {"_id": opportunity["_id"]},
                {
                    "$set": {
                        "portfolio_adjusted_readiness": adjusted,
                    }
                }
            )

    

portfolio_recalculation_service = PortfolioRecalculationService()