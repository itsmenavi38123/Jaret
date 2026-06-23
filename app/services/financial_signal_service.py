from typing import Dict, Any, List

from app.services.signal_engine_service import signal_engine_service
from app.services.signal_shape_mapper import (
signal_shape_mapper,
)
from app.models.financial_signal import FinancialSignal
from app.services.signal_state_service import signal_state_service

class FinancialSignalService:

    def _calculate_pressing_score(
        self,
        signal: Dict[str, Any],
    ) -> int:

        severity = signal.get("severity_tier")

        metric_value = signal.get("metric_value")

        threshold = signal.get("threshold")

        if (
            metric_value is not None
            and threshold is not None
            and isinstance(metric_value, (int, float))
            and isinstance(threshold, (int, float))
        ):
            delta = abs(metric_value - threshold)

            if severity == "hard":
                return min(90 + int(delta * 10), 100)

            if severity == "soft":
                return min(60 + int(delta * 10), 89)

        if severity == "hard":
            return 90

        if severity == "soft":
            return 60

        return 30

    def _determine_state(
        self,
        signal: Dict[str, Any],
    ) -> str:

        severity = signal.get(
            "severity_tier",
        )

        if severity == "hard":
            return "pressing"

        if severity == "soft":
            return "building"

        return "stable"

    def _flatten_signals(
        self,
        signal_surfaces: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:

        signals: List[Dict[str, Any]] = []

        for signal_group in signal_surfaces.values():

            for signal in signal_group or []:

                signal_id = signal.get(
                    "signal_id",
                )

                enriched_signal = FinancialSignal(
                    signal_id=signal_id,
                    title=signal_id.replace("_", " ").title(),
                    state=self._determine_state(
                        signal,
                    ),
                    pressing_score=self._calculate_pressing_score(
                        signal,
                    ),
                    shape_id=signal_shape_mapper.get_shape_id(
                        signal_id,
                    ),
                    severity=signal.get(
                        "severity_tier",
                        "stable",
                    ),
                    metric_value=signal.get(
                        "metric_value",
                    ),
                    threshold=signal.get(
                        "threshold",
                    ),
                    recommended_action=signal.get(
                        "recommended_action",
                    ),
                ).model_dump()

                signals.append(enriched_signal)

        return signals

    async def build_financial_signals(
        self,
        user_id: str,
        metrics: Dict[str, Any],
        classifier_output: Dict[str, Any],
    ) -> Dict[str, Any]:

        signal_surfaces = signal_engine_service.evaluate_signals(
            metrics=metrics,
            classifier_output=classifier_output or {},
        )

        signals = self._flatten_signals(
            signal_surfaces,
        )

        current_signal_ids = [
            signal["signal_id"]
            for signal in signals
        ]

        resolved_signals = await signal_state_service.get_resolved_signals(
            user_id=user_id,
            current_signal_ids=current_signal_ids,
        )

        resolved_signal_cards = []

        for signal_id in resolved_signals:

            resolved_signal_cards.append(
                FinancialSignal(
                    signal_id=signal_id,
                    title=signal_id.replace("_", " ").title(),
                    state="resolved",
                    pressing_score=5,
                    shape_id=signal_shape_mapper.get_shape_id(
                        signal_id,
                    ),
                    severity="resolved",
                ).model_dump()
            )

        signals.extend(
            resolved_signal_cards,
        )

        signals.sort(
            key=lambda item: item.get(
                "pressing_score",
                0,
            ),
            reverse=True,
        )

        hero_signal = None

        if signals:

            top_signal = signals[0]

            hero_signal = {
                **top_signal,
                "headline": top_signal.get(
                    "title",
                    "",
                ),
                "whats_going_on": (
                    f"{top_signal.get('title', '')} detected."
                ),
                "why_it_matters_now": (
                    f"Current value: {top_signal.get('metric_value')}, "
                    f"threshold: {top_signal.get('threshold')}"
                )
                if top_signal.get("metric_value") is not None
                else "",
                "what_to_do": top_signal.get(
                    "recommended_action",
                    "",
                ),
                "expected_impact": "",
                "effort": "medium",
                "confidence": 0.8,
            }

        swipe_signals = signals[1:] if len(signals) > 1 else []

        return {
            "signals": signals,
            "hero_signal": hero_signal,
            "swipe_signals": swipe_signals,
            "signal_count": len(signals),
        }

financial_signal_service = FinancialSignalService()
