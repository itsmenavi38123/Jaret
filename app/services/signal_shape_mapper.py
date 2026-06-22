from typing import Dict


SIGNAL_TO_SHAPE = {
    "cash_runway_compression": "runway_pressure",
    "margin_compression": "margin_compression",
    "customer_concentration_risk": "customer_concentration",
    "vendor_concentration_risk": "vendor_concentration",
    "revenue_trend_reversal": "revenue_decline",
    "food_cost_variance": "cost_pressure",
    "table_turn_rate_decline": "utilization_decline",
    "inventory_shrinkage_spike": "inventory_loss",
    "cart_abandonment_risk": "cart_abandonment",
    "utilization_decline": "utilization_decline",
    "project_margin_variance": "project_margin_pressure",
    "working_capital_decline": "working_capital",
    "ar_collection_deterioration": "collections_lagging",
    "cost_spike_on_key_inputs": "cost_pressure",
    "operational_disruption": "operational_disruption",
    "goal_deviation": "goal_deviation",
    "owner_engagement_decline": "owner_engagement",
}


class SignalShapeMapper:

    def get_shape_id(
        self,
        signal_id: str,
    ) -> str:

        return SIGNAL_TO_SHAPE.get(
            signal_id,
            "generic_financial_signal",
        )


signal_shape_mapper = SignalShapeMapper()