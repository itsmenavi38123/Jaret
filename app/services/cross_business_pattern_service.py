from collections import defaultdict
from statistics import mean
from typing import Dict, Any, List

from app.models.decision_log import DecisionLog


class CrossBusinessPatternService:

    async def build_similar_business_patterns(
        self,
        classifier_output: Dict[str, Any],
    ) -> Dict[str, Any]:

        business_type = (
            classifier_output.get("business_type")
            or classifier_output.get("industry")
        )

        if not business_type:

            return {
                "similar_business_patterns": [],
            }

        decisions = await DecisionLog.find().to_list()

        grouped_patterns = defaultdict(list)

        for decision in decisions:

            metadata = decision.metadata or {}

            decision_business_type = metadata.get(
                "business_type",
            )

            if (
                not decision_business_type
                or decision_business_type != business_type
            ):
                continue

            signal_id = decision.signal_id

            if not signal_id:
                continue

            outcome_metrics = (
                decision.outcome_metrics or {}
            )

            grouped_patterns[signal_id].append({
                "outcome_summary": decision.outcome_summary,
                "outcome_metrics": outcome_metrics,
            })

        aggregated_patterns = []

        for signal_id, outcomes in grouped_patterns.items():

            improvement_scores = []

            for outcome in outcomes:

                metrics = outcome.get(
                    "outcome_metrics",
                    {},
                )

                improvement = metrics.get(
                    "improvement_score",
                )

                if isinstance(
                    improvement,
                    (int, float),
                ):
                    improvement_scores.append(
                        improvement,
                    )

            avg_improvement = (
                mean(improvement_scores)
                if improvement_scores
                else None
            )

            aggregated_patterns.append({
                "signal_id": signal_id,
                "sample_size": len(outcomes),
                "average_improvement_score": round(avg_improvement, 2)
                if avg_improvement is not None
                else None,
                "pattern_summary": (
                    f"Businesses similar to this commonly improved after responding to {signal_id}."
                ),
            })

        return {
            "similar_business_patterns": aggregated_patterns,
        }


cross_business_pattern_service = CrossBusinessPatternService()