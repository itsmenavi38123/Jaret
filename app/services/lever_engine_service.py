from typing import Dict, Any, List

from app.services.lever_library import LEVER_LIBRARY


class LeverEngineService:

    def _resolve_business_context(
        self,
        classifier_output: Dict[str, Any],
    ) -> str:

        tags = classifier_output.get(
            "tags",
            [],
        )

        if "professional_services" in tags:
            return "professional_services"

        if "food_beverage" in tags:
            return "food_beverage"

        if "retail" in tags:
            return "retail"

        return "default"

    def attach_levers(
        self,
        signal_surfaces: Dict[str, List[Dict[str, Any]]],
        classifier_output: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:

        business_context = self._resolve_business_context(
            classifier_output,
        )

        updated_surfaces = {}

        for surface_name, signals in (signal_surfaces or {}).items():

            updated_signals = []

            for signal in signals or []:

                signal_id = signal.get(
                    "signal_id",
                )

                severity = signal.get(
                    "severity_tier",
                )

                signal_library = LEVER_LIBRARY.get(
                    signal_id,
                    {},
                )

                severity_library = signal_library.get(
                    severity,
                    {},
                )

                lever_text = severity_library.get(
                    business_context,
                )

                if not lever_text:
                    lever_text = severity_library.get(
                        "default",
                    )

                signal["lever"] = lever_text

                updated_signals.append(signal)

            updated_surfaces[surface_name] = updated_signals

        return updated_surfaces


lever_engine_service = LeverEngineService()