TIER_A_SIGNAL_LIBRARY = [
    {
        "signal_id": "cash_runway_compression",
        "severity_tier": "hard",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "runway_months",
            "operator": "<",
            "threshold": 3,
        },
        "recommended_action": "Reduce burn and improve cash reserves immediately.",
    },
    {
        "signal_id": "customer_concentration_risk",
        "severity_tier": "hard",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "top_customer_revenue_pct",
            "operator": ">",
            "threshold": 40,
        },
        "recommended_action": "Diversify customer base to reduce dependency risk.",
    },
    {
        "signal_id": "vendor_concentration_risk",
        "severity_tier": "soft",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "top_vendor_expense_pct",
            "operator": ">",
            "threshold": 35,
        },
        "recommended_action": "Reduce operational dependency on a single vendor.",
    },
    {
        "signal_id": "margin_compression",
        "severity_tier": "hard",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "gross_margin_pct",
            "operator": "<",
            "threshold": 0.25,
        },
        "recommended_action": "Review pricing and cost structure.",
    },
    {
        "signal_id": "revenue_trend_reversal",
        "severity_tier": "soft",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "revenue_growth_pct",
            "operator": "<",
            "threshold": -0.1,
        },
        "recommended_action": "Investigate declining sales momentum.",
    },
]

TIER_B_SIGNAL_LIBRARY = [
    {
        "signal_id": "food_cost_variance",
        "severity_tier": "soft",
        "applicability_hint": ["food_beverage"],
        "detection_pattern": {
            "metric": "food_cost_pct",
            "operator": ">",
            "threshold": 0.35,
        },
        "recommended_action": "Review supplier pricing and menu profitability.",
    },
    {
        "signal_id": "table_turn_rate_decline",
        "severity_tier": "soft",
        "applicability_hint": ["food_beverage"],
        "detection_pattern": {
            "metric": "table_turn_rate",
            "operator": "<",
            "threshold": 2,
        },
        "recommended_action": "Improve seating efficiency and service flow.",
    },
    {
        "signal_id": "inventory_shrinkage_spike",
        "severity_tier": "hard",
        "applicability_hint": ["retail"],
        "detection_pattern": {
            "metric": "inventory_shrinkage_pct",
            "operator": ">",
            "threshold": 0.08,
        },
        "recommended_action": "Audit inventory controls and loss prevention.",
    },
    {
        "signal_id": "cart_abandonment_risk",
        "severity_tier": "soft",
        "applicability_hint": ["retail_ecommerce"],
        "detection_pattern": {
            "metric": "cart_abandonment_pct",
            "operator": ">",
            "threshold": 0.7,
        },
        "recommended_action": "Optimize checkout funnel and remarketing flows.",
    },
    {
        "signal_id": "utilization_decline",
        "severity_tier": "soft",
        "applicability_hint": ["professional_services"],
        "detection_pattern": {
            "metric": "utilization_rate",
            "operator": "<",
            "threshold": 0.6,
        },
        "recommended_action": "Increase billable utilization and pipeline conversion.",
    },
    {
        "signal_id": "project_margin_variance",
        "severity_tier": "soft",
        "applicability_hint": ["professional_services"],
        "detection_pattern": {
            "metric": "project_margin_pct",
            "operator": "<",
            "threshold": 0.15,
        },
        "recommended_action": "Review pricing, delivery efficiency, and scope control.",
    },
]