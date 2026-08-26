# backend/app/demo_data/demo_fitness.py
"""
Complete spec-compliant demo payload for Business #7: Southpoint Fitness Studio (demo-fitness).
Follows exact FA V6 schemas (DASHBOARD MODE, INSIGHTS MODE, DRAWER MODE), Demand Forecast (v9 Split), Business Health, 16-section Business Profile, Opportunities V2 (Research Scout V3.1), and Scenario Lab.
"""

SOUTHPOINT_FITNESS_PAYLOADS = {
    "account": {
        "login_label": "demo-fitness",
        "business_name": "Southpoint Fitness Studio",
        "email": "demo-fitness@lightsignal.app",
        "industry": "Boutique Group Fitness Studio",
        "owner": "Jess & Carlos Duarte",
        "is_demo": True,
    },
    
    # 1. DASHBOARD MODE PAYLOAD
    "dashboard": {
        "summary": "Southpoint Fitness studio MRR is $44,000 MTD across 342 active members. Monthly churn creep (3.8% -> 6.1%) from new local competitor is primary focus.",
        "kpis": {
            "revenue_mtd": {"value": 44000.0, "prior_value": 45800.0, "format_type": "currency", "link": "/overview#revenue"},
            "net_margin_pct": {"value": 0.175, "prior_value": 0.198, "format_type": "percentage", "link": "/overview#margin"},
            "cash": {"value": 48000.0, "prior_value": 51200.0, "format_type": "currency", "link": "/overview#cash"},
            "runway_months": {"value": 10.5, "prior_value": 11.2, "format_type": "months", "link": "/overview#runway"},
            "ai_health_score": {"value": 81, "prior_value": 85, "format_type": "score", "link": "/overview#health"},
        },
        "alerts": [
            {
                "severity": "critical",
                "type": "risk",
                "message": "Monthly member churn rate increased from 3.8% to 6.1% (21 cancellations)",
                "icon": "🔴"
            },
            {
                "severity": "below_average",
                "type": "warning",
                "message": "Failed billing batch cluster: 8 card expiries ($1,270 uncollected MRR)",
                "icon": "🟡"
            },
            {
                "severity": "above_average",
                "type": "positive",
                "message": "Corporate wellness contract added +18 recurring members ($2,860/mo MRR)",
                "icon": "🟢"
            }
        ],
        "insight_pairs": [
            {
                "head": "Competitor Churn Creep (6.1% Rate)",
                "problem": "Monthly cancellation rate rose from 3.8% to 6.1% following opening of new competitor 1 mile away, costing 21 member drops ($3,340/mo lost MRR).",
                "solution": "Launch a member retention campaign with 90-day progress check-ins and lock-in rates for annual contracts."
            },
            {
                "head": "Failed Payment Billing Batch Recovery",
                "problem": "First-of-month credit card expiry cluster caused 8 billing declines representing $1,270 in uncollected recurring dues.",
                "solution": "Configure automated SMS payment retry sequence and update billing card prompts in member portal."
            }
        ],
        "opportunities": [
            {
                "head": "Midday 'Lunch Express' Class Utilization",
                "body": "Midday class fill increased from 31% to 44% during pilot; adding 45-minute express slots captures remote worker demand."
            }
        ],
        "what_changed": [
            "Member churn rate expanded to 6.1% driven by new local gym opening.",
            "Corporate contract added +18 new members, offsetting 85% of monthly cancellations."
        ],
        "missing_data_notice": None
    },

    # 2. INSIGHTS MODE PAYLOAD
    "insights_mode": {
        "profitability_banner": {
            "status": "above_average",
            "headline": "Predictable $44K recurring MRR base; churn prevention is top 90-day priority.",
            "supporting_text": "Class coach cost at $65/class; corporate wellness addition stabilizes net member count at 342.",
            "missing_data_notice": None
        },
        "items": [
            {
                "signal_id": "member_churn_spike",
                "pressing_score": 87,
                "tier": "tier_1",
                "headline": "Monthly Churn Creep to 6.1% ($3,340/mo Lost MRR)",
                "whats_going_on": "Mindbody membership records show 21 cancellations this month (6.1% churn vs 3.8% baseline) coinciding with a new boutique gym opening in Ballast Point.",
                "why_it_matters_now": "Sustained 6%+ churn erodes the 342 member baseline below the breakeven threshold of 310 members within 4 months.",
                "what_to_do": "Launch a member feedback exit survey, introduce quarterly progress assessments, and offer 12-month contract rate locks.",
                "expected_impact": {
                    "value_text": "+$2,100/mo MRR preserved",
                    "calculation_basis": "Reducing churn back under 4.0% preserves 13 members monthly at $159 average dues."
                },
                "effort": "quick_win",
                "confidence": "high",
                "directive": {
                    "shape_id": "churn_trend_line",
                    "state": "active",
                    "theme": "critical",
                    "numbers": {"baseline_churn": 3.8, "current_churn": 6.1, "target_churn": 3.5},
                    "labels": {"baseline": "Normal Churn", "current": "Current Spike", "target": "Target Goal"}
                }
            }
        ],
        "missing_data_notice": None
    },

    # 3. DRAWER MODE PAYLOAD
    "drawer_mode": {
        "revenue": {
            "value_text": "$44,000",
            "status_badge": {"label": "Recurring MRR", "severity": "above_average"},
            "headline_read": "Revenue holds at $44.0K MTD; 88% membership MRR, 8% drop-ins, 4% retail.",
            "benchmarks": {
                "peer_avg": "$38,500/mo",
                "sba_metric": "Top performance for Tampa boutique fitness studios",
                "position": "above",
                "gap_text": "14.3% ahead of regional studio benchmark"
            },
            "drivers": [
                {"description": "Unlimited & 8-class recurring memberships (88% share)", "impact": "+$38,720", "category": "Membership MRR"},
                {"description": "Class drop-in passes (8% share)", "impact": "+$3,520", "category": "Drop-Ins"},
                {"description": "Apparel & supplement retail (4% share)", "impact": "+$1,760", "category": "Retail"}
            ],
            "actions": [
                {"description": "Deploy automated card retry sequence for 8 failed credit card billings", "priority": "high", "effort": "quick_win"}
            ]
        }
    },

    # 4. DEMAND FORECAST PAYLOAD
    "demand_forecast": {
        "metrics": {
            "forecast_series": [55000.0, 48400.0, 44000.0, 41800.0, 39600.0, 37400.0, 37400.0, 39600.0, 46200.0, 44000.0, 41800.0, 39600.0]
        },
        "flags": [
            {"severity": "red", "title": "Member Churn Rate Creep (6.1%)"},
            {"severity": "amber", "title": "First-of-Month Failed Billing Batch (8 Cards)"}
        ],
        "data": {
            "historical_revenue": [
                {"date": "2026-01-01", "amount": 55000.0},
                {"date": "2026-02-01", "amount": 48400.0},
                {"date": "2026-03-01", "amount": 44000.0},
                {"date": "2026-04-01", "amount": 44000.0}
            ]
        },
        "agentOutput": {
            "tab_label": "Demand Forecast",
            "demand_unit": "revenue",
            "windows": [
                {
                    "window": "This Weekend",
                    "severity": "above_average",
                    "hero": {
                        "eyebrow": "Weekend Demand Read",
                        "headline": "Projected weekend gym attendance of 340 visits across personal training & group classes.",
                        "expected_value": "$4,200",
                        "expected_unit": "revenue",
                        "volume_forecast": 340,
                        "demand_unit": "Check-ins",
                        "confidence_pct": 90,
                        "confidence_label": "High",
                        "anchor": "Anchored in Mindbody turnstile check-ins & trainer session bookings."
                    },
                    "swing_factor": {
                        "headline": "Saturday Morning Bootcamp Special (+28 check-ins)",
                        "delta_text": "+$850",
                        "direction": "up",
                        "reasoning": "Special weekend guest trainer workshop boosting drop-in pass sales."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "Schedule assistant coach & stock protein smoothie bar", "severity": "above_average"},
                        "whats_moving": {"summary": "2 key demand drivers (Saturday Bootcamp, New Year challenge milestone)", "severity": "above_average"},
                        "breakdown": {"summary": "80% recurring membership, 14% personal training, 6% drop-in passes", "severity": "above_average"},
                        "track_record": {"summary": "Fitness forecast accuracy ran within 2.3% over past 4 weekends", "severity": "above_average"},
                        "world_scan": {"summary": "Sunny 70°F weekend encouraging outdoor turf training", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_fit_bootcamp_01",
                            "action": "Promote 10 remaining Saturday Bootcamp passes on Instagram Stories",
                            "deadline": "Fri, Feb 7",
                            "priority": "high",
                            "tied_to_driver": "Saturday Morning Bootcamp Special",
                            "why_this_much": "Fills remaining 10 spots for 100% capacity.",
                            "dollar_logic": "Captures +$350 in instant drop-in revenue."
                        }
                    ],
                    "whats_moving": [
                        {
                            "name": "Saturday Morning Bootcamp Special",
                            "window": "This Weekend",
                            "severity": "green",
                            "impact_text": "+$850",
                            "reasoning": "High demand for weekend high-intensity group workout.",
                            "source": "Mindbody Class Roster",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 3100.0,
                        "expected_losses": 150.0,
                        "unbooked_demand": 1250.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Gym check-in predictions hit within 2.3% accuracy.",
                        "lean_guidance": "High consistency on weekend morning peak hours."
                    },
                    "world_scan": [
                        {
                            "flag": "Community 5K Run Warmup Sponsorship",
                            "horizon": "Saturday 8 AM - 11 AM",
                            "depends_on": "Trainer staff availability",
                            "action_yet": "Distribute free 3-day guest passes at finish line",
                            "source": "Local Race Association"
                        }
                    ]
                },
                {
                    "window": "Next 30 Days",
                    "severity": "red",
                    "hero": {
                        "eyebrow": "Forward Demand Read",
                        "headline": "Membership recurring MRR tracking at $44,000 MTD; churn retention is key priority.",
                        "expected_value": "$44,000",
                        "expected_unit": "revenue",
                        "confidence_pct": 88,
                        "confidence_label": "High",
                        "anchor": "Anchored in 342 active recurring Mindbody memberships + monthly billing batch history."
                    },
                    "swing_factor": {
                        "headline": "Competitor churn creep (6.1% monthly rate)",
                        "delta_text": "-$3,340",
                        "direction": "down",
                        "reasoning": "21 member cancellations following boutique gym opening 1mi away."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "2 actions to launch retention campaign and recover failed credit card billings", "severity": "critical"},
                        "whats_moving": {"summary": "3 membership drivers (recurring MRR, corporate contract, class drop-ins)", "severity": "above_average"},
                        "breakdown": {"summary": "88% recurring membership dues, 8% drop-in passes, 4% retail", "severity": "above_average"},
                        "track_record": {"summary": "Prior 90-day forecast ran within 2.8% of actual Mindbody billing", "severity": "above_average"},
                        "world_scan": {"summary": "Tampa Ballast Point fitness studio competition tracking high", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_fitness_1",
                            "title": "Launch member retention outreach with 90-day progress assessments",
                            "deadline": "Feb 10",
                            "priority": "high",
                            "tied_to_driver": "Competitor Churn Creep",
                            "why_this_much": "Preserves 13 recurring members monthly to reduce churn under 4.0%.",
                            "dollar_logic": "+$2,100/mo MRR preserved"
                        },
                        {
                            "id": "act_fitness_2",
                            "title": "Deploy automated SMS payment retry for 8 failed credit card billings",
                            "deadline": "Immediate",
                            "priority": "high",
                            "tied_to_driver": "Failed Payment Cluster",
                            "why_this_much": "Recovers $1,270 in uncollected recurring dues from card expiries.",
                            "dollar_logic": "+$1,270 uncollected MRR recovered"
                        }
                    ],
                    "drivers": [
                        {
                            "name": "Competitor Churn Creep",
                            "severity": "red",
                            "window": "Next 30 Days",
                            "impact_text": "-$3,340",
                            "reasoning": "21 member drops following new local gym opening.",
                            "source": "Mindbody Cancellations",
                            "confidence": "high"
                        },
                        {
                            "name": "Failed Payment Cluster",
                            "severity": "amber",
                            "window": "Next 30 Days",
                            "impact_text": "-$1,270",
                            "reasoning": "8 credit card declines in 1st-of-month billing batch.",
                            "source": "Mindbody Merchant Logs",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 38720.0,
                        "expected_losses": 3340.0,
                        "unbooked_demand": 8620.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Prior 90-day forecast ran within 2.8% of actual Mindbody recurring billing.",
                        "lean_guidance": "Slight conservative bias on drop-in class pass sales."
                    },
                    "world_scan": [
                        {
                            "flag": "Tampa Ballast Point Gym Competition",
                            "horizon": "Feb-Apr",
                            "depends_on": "Local boutique gym promotional pricing",
                            "action_yet": "Offer 12-month membership rate lock for existing members",
                            "source": "Local Business & Social Scan"
                        }
                    ]
                }
            ]
        }
    },

    # 5. BUSINESS HEALTH PAYLOAD
    "business_health": {
        "overall_score": 81,
        "status": "Healthy",
        "dimensions": {
            "liquidity": {"score": 84, "label": "Strong", "cash_months": 10.5},
            "profitability": {"score": 79, "label": "Good", "net_margin": 17.5},
            "growth": {"score": 82, "label": "Steady", "yoy_growth": 5.2},
            "efficiency": {"score": 75, "label": "Moderate", "class_fill_pct": "71%"},
            "resilience": {"score": 85, "label": "High", "debt_load": "$0 (No Debt)"}
        }
    },

    # 6. BUSINESS PROFILE PAYLOAD
    "business_profile": {
        "section_1_basics": {
            "business_name": "Southpoint Fitness Studio",
            "legal_entity": "Duarte Fitness Concepts LLC",
            "year_founded": 2021,
            "headquarters": "Tampa, FL (Ballast Point)",
            "website": "https://southpointfitness.com",
            "operating_mode": "Boutique Group Fitness & Membership Studio"
        },
        "section_2_ownership": {
            "owner_name": "Jess & Carlos Duarte",
            "ownership_pct": 100.0,
            "role": "Co-Owners & Lead Head Coaches",
            "years_in_business": 5
        },
        "section_3_industry": {
            "primary_industry": "Fitness & Recreational Sports Centers",
            "naics_code": "713940",
            "niche": "High-Intensity Group Training & Personal Coaching"
        },
        "section_4_operations": {
            "days_open_per_week": 7,
            "operating_hours": "5:30 AM - 7:30 PM (Mon-Fri), 7:00 AM - 1:00 PM (Sat-Sun)",
            "pos_system": "Mindbody Online",
            "studio_capacity": 24
        },
        "section_5_financial": {
            "annual_revenue": 528000.0,
            "gross_margin_pct": 62.0,
            "net_margin_pct": 17.5,
            "monthly_cash_flow": 7700.0,
            "accounting_software": "QuickBooks Online"
        },
        "section_6_assets": {
            "real_estate": "Leased commercial studio space (3,200 sq ft)",
            "equipment_value": 75000.0,
            "inventory_valuation": 4500.0
        },
        "section_7_customers": {
            "customer_type": "B2C Active Monthly Members",
            "average_ticket": 159.0,
            "monthly_transacting_customers": 342
        },
        "section_8_risk": {
            "top_cost_exposure": "Monthly Member Churn Creep (6.1%)",
            "capacity_risk": "First-of-month credit card decline cluster"
        },
        "section_9_capacity": {
            "studio_capacity_per_class": 24,
            "weekly_classes_offered": 36,
            "current_class_fill_pct": 71.0
        },
        "section_10_opportunity_readiness": {
            "corporate_wellness": "Active (+18 members added)",
            "midday_class_expansion": "High potential (remote worker market)"
        },
        "section_11_goals": {
            "target_annual_revenue": 620000.0,
            "margin_target": 20.0,
            "growth_focus": "Corporate wellness partnerships & churn reduction"
        },
        "section_12_pricing": {
            "pricing_tier": "Boutique Premium",
            "price_points": {"unlimited_monthly": "$179", "8_class_pack": "$139", "drop_in": "$25"}
        },
        "section_13_team": {
            "full_time_staff": 2,
            "part_time_staff": 5,
            "key_personnel": "Head Coach, Studio Manager, Group Fitness Instructors"
        },
        "section_14_marketing": {
            "primary_channels": "Local Instagram, Mindbody App, Community Corporate Wellness",
            "monthly_ad_budget": 600.0
        },
        "section_15_owner_prefs": {
            "risk_tolerance": "Moderate",
            "funding_preference": "Reinvest studio profits, zero debt"
        },
        "section_16_docs": {
            "connected_systems": ["Mindbody Online", "QuickBooks Online"],
            "verification_status": "Verified"
        }
    },

    # 7. OPPORTUNITIES V2 PAYLOAD
    "opportunities": {
        "kpis": {
            "active_opportunities": {"count": 6, "descriptor": "Browse studio matches"},
            "new_this_week": {"count": 2, "label": "2 new this week"},
            "total_potential_value": "$18,600",
            "avg_fit_score": 88,
            "event_readiness_index": 86,
            "historical_roi": {"multiplier": "3.2x", "sample_size": 4}
        },
        "recommended_hero": {
            "id": "opp_fitness_hero",
            "type": "Vendor Program",
            "box_type": "Direct Match",
            "out_box": False,
            "title": "Tampa Bay Corporate Wellness Partnership Program",
            "source": "Tampa Business Journal / Corporate Health Network",
            "match_score": 92,
            "readiness_score": 88,
            "data_trust_indicator": "Verified",
            "risk_level": "Low",
            "drive_time_minutes": 10,
            "distance_miles": 2.5,
            "expires_at": "Closes in 16 days",
            "estimated_revenue": "$6,800/mo corporate MRR",
            "listed_fee": "$0 (Direct Partnership)",
            "why_reason_codes": ["Adds recurring corporate members to fill midday 12 PM class slots"],
            "risk_signals": ["Requires monthly attendance verification reports"],
            "verify_flag": False,
            "verify_flag_message": None,
            "registration_url": "https://tampabusinessjournal.org/corporate-wellness",
            "source_url": "https://tampabusinessjournal.org/events"
        },
        "more_matches": [],
        "recommended": [
            {
                "id": "opp_fitness_1",
                "title": "Midday 'Lunch Express' Class Utilization",
                "impact": "+$2,860/mo corporate MRR",
                "strategic_fit": "Fills unbooked 12 PM studio capacity",
                "execution_steps": [
                    "Launch 45-minute Lunch Express class schedule",
                    "Market corporate membership packages to 8 nearby office complexes"
                ],
                "risk_rating": "Low"
            }
        ],
        "selected_tracked": [
            {
                "id": "track_fitness_1",
                "title": "Tampa Corporate Wellness Program",
                "type": "Vendor Program",
                "status": "Tracked",
                "estimated_revenue": "$6,800/mo",
                "next_checkpoint": "Day 4 check-in in 2 days"
            }
        ],
        "portfolio_summary": {
            "active_count": 1,
            "past_count": 4,
            "total_committed_dollars": "$6,800"
        }
    },

    # 8. SCENARIOS PAYLOAD
    "scenarios": {
        "scenario_id": "scen_fitness_corp",
        "confidence": 90,
        "risk": "Low",
        "impact_cards": [
            {"label": "Corporate MRR Added", "value": "+$2,860", "direction": "up"},
            {"label": "Net Churn Offset", "value": "85% Covered", "direction": "up"},
            {"label": "Net Margin Expansion", "value": "+2.2%", "direction": "up"}
        ]
    }
}
