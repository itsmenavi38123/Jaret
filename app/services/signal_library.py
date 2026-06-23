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
    {
        "signal_id": "working_capital_decline",
        "severity_tier": "hard",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "quick_ratio",
            "operator": "<",
            "threshold": 1,
        },
        "recommended_action": "Improve liquidity and working capital management.",
    },
    {
        "signal_id": "ar_collection_deterioration",
        "severity_tier": "soft",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "ccc_days",
            "operator": ">",
            "threshold": 60,
        },
        "recommended_action": "Accelerate collections and reduce receivable aging.",
    },
    {
        "signal_id": "cost_spike_on_key_inputs",
        "severity_tier": "hard",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "key_input_cost_increase_pct",
            "operator": ">",
            "threshold": 20,
        },
        "recommended_action": "Review supplier pricing and renegotiate major cost inputs.",
    },
    {
        "signal_id": "operational_disruption",
        "severity_tier": "soft",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "operational_disruption_score",
            "operator": ">",
            "threshold": 50,
        },
        "recommended_action": "Address operational bottlenecks affecting delivery and execution.",
    },
    {
        "signal_id": "goal_deviation",
        "severity_tier": "soft",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "goal_completion_pct",
            "operator": "<",
            "threshold": 70,
        },
        "recommended_action": "Review business goals and create corrective actions for missed targets.",
    },
    {
        "signal_id": "owner_engagement_decline",
        "severity_tier": "soft",
        "applicability_hint": ["all"],
        "detection_pattern": {
            "metric": "owner_engagement_score",
            "operator": "<",
            "threshold": 50,
        },
        "recommended_action": "Increase review cadence and engagement with business performance metrics.",
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