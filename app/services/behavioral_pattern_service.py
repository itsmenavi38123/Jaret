from collections import Counter
from datetime import datetime
from statistics import mean
from typing import Dict, Any, List

from app.services.decision_log_service import (
    decision_log_service,
)


class BehavioralPatternService:

    async def compute_owner_patterns(
        self,
        user_id: str,
    ) -> Dict[str, Any]:

        decisions = await decision_log_service.list_user_decisions(
            user_id=user_id,
            limit=200,
        )

        if not decisions:
            return {
                "decision_velocity": None,
                "preferred_signal_types": [],
                "consultation_patterns": [],
                "owner_behavior_style": "unknown",
                "ignored_signal_patterns": [],
            }

        signal_counter = Counter()

        consultation_counter = Counter()

        owner_states = []

        response_intervals = []

        ignored_signals = []

        sorted_decisions = sorted(
            decisions,
            key=lambda x: x.created_at,
        )

        previous_time = None

        for decision in sorted_decisions:

            signal_id = decision.signal_id

            if signal_id:
                signal_counter[signal_id] += 1

            for consultation in (
                decision.consultation_sources or []
            ):
                consultation_counter[consultation] += 1

            if decision.owner_state:
                owner_states.append(
                    decision.owner_state,
                )

            if (
                decision.metadata
                and decision.metadata.get("ignored")
            ):
                ignored_signals.append(
                    signal_id,
                )

            current_time = decision.created_at

            if previous_time:

                delta_hours = (
                    current_time - previous_time
                ).total_seconds() / 3600

                response_intervals.append(
                    delta_hours,
                )

            previous_time = current_time

        avg_response_time = (
            mean(response_intervals)
            if response_intervals
            else None
        )

        behavior_style = "balanced"

        if avg_response_time is not None:

            if avg_response_time < 24:
                behavior_style = "fast_moving"

            elif avg_response_time > 168:
                behavior_style = "deliberate"

        return {
            "decision_velocity": round(avg_response_time, 2)
            if avg_response_time is not None
            else None,

            "preferred_signal_types": [
                signal
                for signal, _
                in signal_counter.most_common(5)
            ],

            "consultation_patterns": [
                source
                for source, _
                in consultation_counter.most_common(5)
            ],

            "owner_behavior_style": behavior_style,

            "common_owner_states": (
                Counter(owner_states).most_common(3)
            ),

            "ignored_signal_patterns": (
                Counter(ignored_signals).most_common(5)
            ),
        }


behavioral_pattern_service = BehavioralPatternService()