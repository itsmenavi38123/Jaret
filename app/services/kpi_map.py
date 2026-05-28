DEFAULT_KPI_PROFILE = {
    "categories": {
        "financial_health": {
            "metrics": [
                {"metric": "net_margin_pct", "weight": 0.4},
                {"metric": "runway_months", "weight": 0.35},
                {"metric": "quick_ratio", "weight": 0.25},
            ]
        },
        "operational_health": {
            "metrics": [
                {"metric": "inventory_turns", "weight": 0.4},
                {"metric": "ccc_days", "weight": 0.35},
                {"metric": "dso_days", "weight": 0.25},
            ]
        },
        "risk_health": {
            "metrics": [
                {"metric": "runway_months", "weight": 0.5},
                {"metric": "quick_ratio", "weight": 0.5},
            ]
        },
        "growth_health": {
            "metrics": [
                {"metric": "revenue_growth_rate", "weight": 1.0},
            ]
        },
    },
    "category_weights": {
        "financial_health": 0.35,
        "operational_health": 0.25,
        "risk_health": 0.25,
        "growth_health": 0.15,
    },
}


KPI_MAP_CONFIG = {

    "saas": {
        "categories": {
            "financial_health": {
                "metrics": [
                    {"metric": "gross_margin_pct", "weight": 0.35},
                    {"metric": "ltv_cac_ratio", "weight": 0.25},
                    {"metric": "burn_multiple", "weight": 0.2},
                    {"metric": "nrr_pct", "weight": 0.2},
                ]
            },
            "operational_health": {
                "metrics": [
                    {"metric": "uptime_pct", "weight": 0.4},
                    {"metric": "support_efficiency", "weight": 0.3},
                    {"metric": "mrr_growth_velocity", "weight": 0.3},
                ]
            },
            "risk_health": {
                "metrics": [
                    {"metric": "runway_months", "weight": 0.5},
                    {"metric": "quick_ratio", "weight": 0.5},
                ]
            },
            "growth_health": {
                "metrics": [
                    {"metric": "revenue_growth_rate", "weight": 0.5},
                    {"metric": "nrr_pct", "weight": 0.5},
                ]
            },
        },
        "category_weights": {
            "financial_health": 0.3,
            "operational_health": 0.2,
            "risk_health": 0.15,
            "growth_health": 0.35,
        },
    },

    "food_truck": {
        "categories": {
            "financial_health": {
                "metrics": [
                    {"metric": "food_cost_pct", "weight": 0.35},
                    {"metric": "cash_buffer_days", "weight": 0.25},
                    {"metric": "daily_revenue_consistency", "weight": 0.2},
                    {"metric": "gross_margin_pct", "weight": 0.2},
                ]
            },
            "operational_health": {
                "metrics": [
                    {"metric": "inventory_turns", "weight": 0.35},
                    {"metric": "hourly_revenue_pattern", "weight": 0.35},
                    {"metric": "average_ticket", "weight": 0.3},
                ]
            },
            "risk_health": {
                "metrics": [
                    {"metric": "runway_months", "weight": 0.6},
                    {"metric": "quick_ratio", "weight": 0.4},
                ]
            },
            "growth_health": {
                "metrics": [
                    {"metric": "revenue_growth_rate", "weight": 1.0},
                ]
            },
        },
        "category_weights": {
            "financial_health": 0.4,
            "operational_health": 0.25,
            "risk_health": 0.25,
            "growth_health": 0.1,
        },
    },

    "b2b_services": {
        "categories": {
            "financial_health": {
                "metrics": [
                    {"metric": "project_margin", "weight": 0.35},
                    {"metric": "ar_collection_efficiency", "weight": 0.25},
                    {"metric": "recurring_revenue_ratio", "weight": 0.2},
                    {"metric": "gross_margin_pct", "weight": 0.2},
                ]
            },
            "operational_health": {
                "metrics": [
                    {"metric": "utilization_rate", "weight": 0.35},
                    {"metric": "billable_hours", "weight": 0.35},
                    {"metric": "realization_rate", "weight": 0.3},
                ]
            },
            "risk_health": {
                "metrics": [
                    {"metric": "runway_months", "weight": 0.5},
                    {"metric": "quick_ratio", "weight": 0.5},
                ]
            },
            "growth_health": {
                "metrics": [
                    {"metric": "revenue_growth_rate", "weight": 1.0},
                ]
            },
        },
        "category_weights": {
            "financial_health": 0.35,
            "operational_health": 0.3,
            "risk_health": 0.2,
            "growth_health": 0.15,
        },
    },
}