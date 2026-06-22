from typing import Dict, Any, List

from app.services.signal_library import (
    TIER_A_SIGNAL_LIBRARY,
    TIER_B_SIGNAL_LIBRARY,
)


class SignalEngineService:

    def _evaluate_rule(
        self,
        value: Any,
        operator: str,
        threshold: Any,
    ) -> bool:

        if value is None:
            return False

        try:

            if operator == ">":
                return value > threshold

            if operator == "<":
                return value < threshold

            if operator == ">=":
                return value >= threshold

            if operator == "<=":
                return value <= threshold

            if operator == "==":
                return value == threshold

        except Exception:
            return False

        return False

    def _is_signal_applicable(
        self,
        signal: Dict[str, Any],
        classifier_output: Dict[str, Any],
    ) -> bool:

        applicability = signal.get(
            "applicability_hint",
            [],
        )

        if "all" in applicability:
            return True

        business_tags = classifier_output.get(
            "tags",
            [],
        )

        for tag in applicability:

            if tag in business_tags:
                return True

        return False

    def evaluate_signals(
        self,
        metrics: Dict[str, Any],
        classifier_output: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:

        hard_signals = []
        soft_signals = []
        stable_signals = []

        tier_b_signals_active = set(
            classifier_output.get(
                "tier_b_signals_active",
                [],
            )
        )

        combined_library = list(
            TIER_A_SIGNAL_LIBRARY
        )

        for signal in TIER_B_SIGNAL_LIBRARY:

            if signal.get(
                "signal_id",
            ) in tier_b_signals_active:

                combined_library.append(
                    signal,
                )

        for signal in combined_library:

            if not self._is_signal_applicable(
                signal,
                classifier_output,
            ):
                continue

            detection_pattern = signal.get(
                "detection_pattern",
                {},
            )

            metric_name = detection_pattern.get(
                "metric",
            )

            operator = detection_pattern.get(
                "operator",
            )

            threshold = detection_pattern.get(
                "threshold",
            )

            metric_value = metrics.get(
                metric_name,
            )

            signal_triggered = self._evaluate_rule(
                value=metric_value,
                operator=operator,
                threshold=threshold,
            )

            if not signal_triggered:
                continue

            signal_payload = {
                "signal_id": signal.get("signal_id"),
                "severity_tier": signal.get("severity_tier"),
                "metric": metric_name,
                "metric_value": metric_value,
                "threshold": threshold,
                "recommended_action": signal.get("recommended_action"),
            }

            severity = signal.get("severity_tier")

            if severity == "hard":
                hard_signals.append(signal_payload)

            elif severity == "soft":
                soft_signals.append(signal_payload)

            else:
                stable_signals.append(signal_payload)

        return {
            "active_health_alerts": hard_signals,
            "priority_watch_areas": soft_signals,
            "score_drivers": stable_signals,
        }


signal_engine_service = SignalEngineService()