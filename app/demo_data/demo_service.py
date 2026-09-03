# backend/app/demo_data/demo_service.py
"""
Complete spec-compliant demo payload for Business #3: Ironwood Plumbing & Heating (demo-service).
Follows exact FA V6 schemas (DASHBOARD MODE, INSIGHTS MODE, DRAWER MODE), Demand Forecast (v9 Split), Business Health, 16-section Business Profile, Opportunities V2 (Research Scout V3.1), and Scenario Lab.
"""

IRONWOOD_PLUMBING_PAYLOADS = {
    "account": {
        "login_label": "demo-service",
        "business_name": "Ironwood Plumbing & Heating",
        "email": "demo-service@lightsignal.app",
        "industry": "Plumbing & HVAC Contractor",
        "owner": "Marcus Boone",
        "is_demo": True,
    },
    
    # 1. DASHBOARD MODE PAYLOAD
    "dashboard": {
        "summary": "Ironwood Plumbing revenue reached $115,000 MTD. Accounts receivable aging expanded as key commercial client slipped to 68 days ($31,000 AR).",
        "kpis": {
            "revenue_mtd": {"value": 115000.0, "prior_value": 110000.0, "format_type": "currency", "link": "/overview#revenue"},
            "net_margin_pct": {"value": 0.185, "prior_value": 0.192, "format_type": "percentage", "link": "/overview#margin"},
            "cash": {"value": 142000.0, "prior_value": 138000.0, "format_type": "currency", "link": "/overview#cash"},
            "runway_months": {"value": 14.5, "prior_value": 15.0, "format_type": "months", "link": "/overview#runway"},
            "ai_health_score": {"value": 81, "prior_value": 84, "format_type": "score", "link": "/overview#health"},
        },
        "alerts": [
            {
                "severity": "critical",
                "type": "risk",
                "message": "Property management AR slipped to 68 days ($31,000 balance overdue)",
                "icon": "🔴"
            },
            {
                "severity": "below_average",
                "type": "warning",
                "message": "Fleet fuel expense +11% impacting overall service call margin",
                "icon": "🟡"
            },
            {
                "severity": "above_average",
                "type": "positive",
                "message": "Trenchless replacement project landed $18,500 one-time revenue bump",
                "icon": "🟢"
            }
        ],
        "insight_pairs": [
            {
                "head": "Accounts Receivable Aging Spike (68 Days)",
                "problem": "Anchor property management client ($31,000 balance, 18% revenue share) slipped past 60-day terms, raising total outstanding AR to $118,000.",
                "solution": "Enforce strict credit-hold on new service dispatches for accounts over 60 days and require 50% deposit on major replacement jobs."
            },
            {
                "head": "Unfilled Licensed Tech Capacity Bottleneck",
                "problem": "Open licensed technician position (unfilled 3 months) caps concurrent service job capacity at 7 teams during peak summer AC season.",
                "solution": "Increase sign-on bonus for licensed HVAC tech and adjust field technician call scheduling."
            }
        ],
        "opportunities": [
            {
                "head": "Trenchless Pipe Camera Utilization",
                "body": "Market high-margin trenchless replacement services ($18,500 average ticket) to residential owners with aging sewer lines."
            }
        ],
        "what_changed": [
            "DSO expanded from 41 to 52 days driven by delayed commercial payments.",
            "Revenue MTD grew 4.5% supported by heavy summer HVAC service calls."
        ],
        "missing_data_notice": None
    },

    # 2. INSIGHTS MODE PAYLOAD
    "insights_mode": {
        "profitability_banner": {
            "status": "above_average",
            "headline": "Strong service revenue ($115K MTD); AR collection aging requires immediate action.",
            "supporting_text": "Gross margin at 55.0% on service calls; total AR balance stands at $118,000 with $31,000 over 60 days.",
            "missing_data_notice": None
        },
        "items": [
            {
                "signal_id": "ar_aging_risk",
                "pressing_score": 88,
                "tier": "tier_1",
                "headline": "Commercial AR Slipped to 68 Days ($31K Outstanding)",
                "whats_going_on": "Ironwood's largest property-management account (18% revenue concentration) has delayed payment past NET-30 terms to 68 days. Total outstanding customer AR is currently $118,000.",
                "why_it_matters_now": "Carrying $118K in unpaid invoices ties up working capital required for biweekly payroll ($39K/pay period) and vendor parts buys.",
                "what_to_do": "Initiate direct phone outreach to client accounting lead, place a temporary hold on non-emergency calls, and mandate NET-15 terms on new proposals.",
                "expected_impact": {
                    "value_text": "+$31,000 cash collected",
                    "calculation_basis": "Collecting overdue 60+ day balances brings DSO back down to target 30-day window."
                },
                "effort": "quick_win",
                "confidence": "high",
                "directive": {
                    "shape_id": "ar_aging_waterfall",
                    "state": "active",
                    "theme": "critical",
                    "numbers": {"current_30d": 62000.0, "aging_31_60": 25000.0, "overdue_60p": 31000.0},
                    "labels": {"current": "0-30 Days", "aging": "31-60 Days", "overdue": "60+ Days (Overdue)"}
                }
            }
        ],
        "missing_data_notice": None
    },

    # 3. DRAWER MODE PAYLOAD
    "drawer_mode": {
        "revenue": {
            "value_text": "$115,000",
            "status_badge": {"label": "Strong Volume", "severity": "above_average"},
            "headline_read": "Revenue steady at $115K MTD; service calls represent 55% of volume, replacement jobs 45%.",
            "benchmarks": {
                "peer_avg": "$98,000/mo",
                "sba_metric": "Top tier Columbus trade contractor",
                "position": "above",
                "gap_text": "17.3% above regional contractor benchmark"
            },
            "drivers": [
                {"description": "Residential & commercial service calls (55% share)", "impact": "+$63,250", "category": "Service Calls"},
                {"description": "HVAC & plumbing replacement installs (45% share)", "impact": "+$51,750", "category": "Replacements"}
            ],
            "actions": [
                {"description": "Follow up directly on $31,000 overdue commercial property invoices", "priority": "high", "effort": "quick_win"}
            ]
        }
    },

    # 4. DEMAND FORECAST PAYLOAD
    "demand_forecast": {
        "metrics": {
            "forecast_series": [143750.0, 120750.0, 103500.0, 92000.0, 103500.0, 120750.0, 149500.0, 132250.0, 109250.0, 92000.0, 103500.0, 115000.0]
        },
        "flags": [
            {"severity": "red", "title": "Commercial AR Slipped to 68 Days ($31K)"},
            {"severity": "amber", "title": "Unfilled Licensed HVAC Tech Position"}
        ],
        "data": {
            "historical_revenue": [
                {"date": "2026-01-01", "amount": 143750.0},
                {"date": "2026-02-01", "amount": 120750.0},
                {"date": "2026-03-01", "amount": 103500.0},
                {"date": "2026-04-01", "amount": 115000.0}
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
                        "headline": "Projected weekend emergency dispatch revenue of $18,500 across HVAC & plumbing.",
                        "expected_value": "$18,500",
                        "expected_unit": "revenue",
                        "volume_forecast": 24,
                        "demand_unit": "Dispatches",
                        "confidence_pct": 93,
                        "confidence_label": "High",
                        "anchor": "Anchored in Jobber dispatch logs + 3-year winter freeze service calls."
                    },
                    "swing_factor": {
                        "headline": "Winter Freeze Warning (+35% emergency calls)",
                        "delta_text": "+$4,200",
                        "direction": "up",
                        "reasoning": "Sub-freezing temperatures driving residential pipe freeze & furnace outage calls."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "Stage 2 on-call technicians & prep emergency pipe repair inventory", "severity": "above_average"},
                        "whats_moving": {"summary": "2 key demand drivers (Freeze warning, commercial maintenance contracts)", "severity": "above_average"},
                        "breakdown": {"summary": "65% emergency repair, 25% commercial HVAC, 10% scheduled maintenance", "severity": "above_average"},
                        "track_record": {"summary": "Emergency forecast accuracy ran within 1.9% over past 3 freezes", "severity": "above_average"},
                        "world_scan": {"summary": "22°F overnight low forecast across Dallas metro area", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_service_dispatch_01",
                            "action": "Assign 2 additional technicians to Friday & Saturday overnight emergency shifts",
                            "deadline": "Fri, Feb 7",
                            "priority": "high",
                            "tied_to_driver": "Winter Freeze Warning",
                            "why_this_much": "Prevents missed $350/hr emergency dispatch calls.",
                            "dollar_logic": "Captures +$4,200 in high-margin emergency service billing."
                        }
                    ],
                    "whats_moving": [
                        {
                            "name": "Winter Freeze Warning",
                            "window": "This Weekend",
                            "severity": "green",
                            "impact_text": "+$4,200",
                            "reasoning": "Overnight low of 22°F triggers surge in furnace & pipe freeze calls.",
                            "source": "National Weather Service",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 12000.0,
                        "expected_losses": 600.0,
                        "unbooked_demand": 7100.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Emergency dispatch predictions hit within 1.9% accuracy.",
                        "lean_guidance": "High precision during severe weather events."
                    },
                    "world_scan": [
                        {
                            "flag": "North Texas Winter Weather Advisory",
                            "horizon": "Friday Night - Sunday Morning",
                            "depends_on": "On-call technician availability & van inventory",
                            "action_yet": "Stock 4 service vans with 3/4-inch copper pipe & fittings",
                            "source": "NWS Dallas Bureau"
                        }
                    ]
                },
                {
                    "window": "Next 30 Days",
                    "severity": "red",
                    "hero": {
                        "eyebrow": "Forward Demand Read",
                        "headline": "Contractor demand tracking strong at $115,000 MTD; AR collection delay is primary liquidity constraint.",
                        "expected_value": "$115,000",
                        "expected_unit": "revenue",
                        "confidence_pct": 89,
                        "confidence_label": "High",
                        "anchor": "Anchored in QBO billing actuals + Jobber field service dispatch schedule."
                    },
                    "swing_factor": {
                        "headline": "Property management account 68-day AR delay",
                        "delta_text": "-$31,000",
                        "direction": "down",
                        "reasoning": "Anchor commercial account delayed payment past 60 days."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "2 actions to collect $31K overdue AR and fill open HVAC tech slot", "severity": "critical"},
                        "whats_moving": {"summary": "3 key service drivers (residential plumbing, commercial HVAC, trenchless jobs)", "severity": "above_average"},
                        "breakdown": {"summary": "55% service calls, 45% equipment replacements", "severity": "above_average"},
                        "track_record": {"summary": "Prior 90-day forecast ran within 3.5% of QBO actuals", "severity": "above_average"},
                        "world_scan": {"summary": "Columbus area summer heat wave driving emergency HVAC service calls", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_ironwood_1",
                            "title": "Initiate credit-hold outreach for $31,000 overdue property management AR",
                            "deadline": "Immediate",
                            "priority": "high",
                            "tied_to_driver": "Commercial AR Aging",
                            "why_this_much": "Collects $31,000 cash to fund biweekly payroll and vendor parts buys.",
                            "dollar_logic": "+$31,000 cash collected"
                        },
                        {
                            "id": "act_ironwood_2",
                            "title": "Offer $2,500 sign-on bonus for open licensed HVAC technician position",
                            "deadline": "Feb 20",
                            "priority": "medium",
                            "tied_to_driver": "Licensed Tech Bottleneck",
                            "why_this_much": "Unlocks 8th concurrent service team for peak summer AC season.",
                            "dollar_logic": "+$8,500/mo capacity sales"
                        }
                    ],
                    "drivers": [
                        {
                            "name": "Commercial AR Aging",
                            "severity": "red",
                            "window": "Next 30 Days",
                            "impact_text": "-$31,000",
                            "reasoning": "Anchor client slipped to 68 days past NET-30 terms.",
                            "source": "QBO AR Aging",
                            "confidence": "high"
                        },
                        {
                            "name": "Licensed Tech Bottleneck",
                            "severity": "amber",
                            "window": "Next 30 Days",
                            "impact_text": "-$8,500",
                            "reasoning": "Open technician position unfilled for 3 months.",
                            "source": "Jobber Dispatch Logs",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 63250.0,
                        "expected_losses": 31000.0,
                        "unbooked_demand": 82750.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Prior 90-day forecast ran within 3.5% of actual QBO revenue.",
                        "lean_guidance": "Slight conservative bias on large trenchless replacement jobs."
                    },
                    "world_scan": [
                        {
                            "flag": "Columbus Regional HVAC Summer Peak",
                            "horizon": "Jun-Aug",
                            "depends_on": "High temperature weather alerts",
                            "action_yet": "Stage AC replacement units in shop inventory",
                            "source": "Local Weather & Trade Scan"
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
            "liquidity": {"score": 85, "label": "Strong", "cash_months": 14.5},
            "profitability": {"score": 82, "label": "Good", "net_margin": 18.5},
            "growth": {"score": 80, "label": "Steady", "yoy_growth": 5.1},
            "efficiency": {"score": 68, "label": "Needs Action", "dso_days": "52 Days"},
            "resilience": {"score": 90, "label": "Excellent", "debt_load": "$0 (No Debt)"}
        }
    },

    # 6. BUSINESS PROFILE PAYLOAD
    "business_profile": {
        "section_01_business_basics": {
            "business_name": "Ironwood Plumbing & Heating",
            "headquarters": "Columbus, OH",
            "years_in_business": "More than 10 years",
            "timezone": "America/New_York",
            "currency": "USD",
            "legal_entity_type": "LLC",
            "ein": "31-9876543",
            "locations": [
                {
                    "name": "Ironwood Central Workshop & Dispatch",
                    "address": "845 N High St, Columbus, OH 43215",
                    "role": "Central Workshop & Dispatch",
                    "status": "active"
                }
            ]
        },
        "section_02_ownership_and_key_people": {
            "ownership_breakdown": "Marcus Boone (100%)",
            "decision_maker": "Marcus Boone, Owner & Master Plumber",
            "bookkeeper_financial_handler": "Buckeye State CPA Group (External)",
            "has_backup_operator": "Yes"
        },
        "section_03_industry_and_model": {
            "business_description": "Licensed master plumbing, HVAC replacement, and trenchless sewer repair contracting service for residential and commercial clients.",
            "revenue_model_description": "Hourly service tickets, fixed-price mechanical installations, commercial maintenance contracts, and trenchless sewer jobs.",
            "target_market_type": "Both",
            "business_stage": "Growing and adding capacity"
        },
        "section_04_operations": {
            "team_size": "Team of 11 to 25",
            "payroll_type": "Mostly employees with some contractors",
            "operating_hours": "Mon-Sat 7am-6pm, Emergency 24/7",
            "growth_limiters": [
                "Staff",
                "Equipment",
                "Time"
            ],
            "single_supplier_dependency": "We have key suppliers but alternatives exist",
            "uses_pos_system": "Yes",
            "space_ownership_status": "Own it",
            "operational_software": [
                "Scheduling software",
                "Project management",
                "Payroll software"
            ],
            "recent_supplier_issues": "No",
            "critical_materials_inputs": "Commercial PVC piping, copper fittings, water heaters, heat pump units, refrigerant."
        },
        "section_05_financial_overview": {
            "accounting_system": "QuickBooks",
            "connect_accounting_now": "Yes",
            "fiscal_year_start": "January to December (all 12 months)",
            "banks_and_lenders": "First Local Bank",
            "business_loan_history": "Yes and currently paying it"
        },
        "section_06_assets_and_equipment": {
            "major_assets": "7x Outfitted Ford Transit Vans, Trenchless Pipe Relining Machine, Ridgid Sewer Cameras, Shop Facility",
            "asset_ownership_status": "Truck is leased, internal equipment is owned",
            "asset_purchase_dates": "Trenchless rig acquired 2021, fleet updated 2020-2023",
            "asset_condition": "Good working condition, regular maintenance performed",
            "leased_monthly_payment": "$500 to $2K"
        },
        "section_07_customers_and_market": {
            "customer_distance": "Across the metro",
            "strongest_seasons": [
                "Spring",
                "Summer",
                "Fall"
            ],
            "customer_acquisition_channels": [
                "Word of mouth",
                "Search / maps",
                "Social media",
                "Repeat regulars"
            ],
            "typical_customers_description": "Residential homeowners needing emergency mechanical repairs and commercial property managers managing multifamily complexes.",
            "monthly_customer_volume": "235",
            "repeat_business_rate": "High",
            "target_customer_types": "Corporate offices looking for weekly lunch catering.",
            "customer_concentration": "No, spread across many",
            "seasonality_level": "A little seasonal",
            "customer_geographic_source": "Within 10–15 miles",
            "opportunity_radius_miles": "25",
            "max_travel_distance_miles": "75",
            "local_opportunity_preference": "Open to nearby areas if high-value",
            "geographic_service_areas": "Franklin County, Delaware County, and Greater Columbus Metro",
            "weather_impact": "High"
        },
        "section_08_risk_and_exposure": {
            "carries_business_insurance": "Yes",
            "critical_dependencies": "Licensed master plumber certification and commercial van fleet uptime",
            "revenue_concentration": "No, spread across many",
            "active_permits_licenses": "State of Ohio Master Plumber License, Class A HVAC Contractor License, City Bonding",
            "in_progress_permits_licenses": "State backflow testing re-certification",
            "local_operating_restrictions": "Designated food zones, noise ordinances after 10 PM"
        },
        "section_09_capacity_and_constraints": {
            "monthly_customer_capacity": "350",
            "could_handle_more_capacity": "Yes, we had plenty of room",
            "current_busy_level": [
                "Around capacity"
            ],
            "operational_slowdown_factors": [
                "Labor",
                "Equipment"
            ],
            "has_active_business_financing": "Yes"
        },
        "section_10_opportunity_readiness": {
            "external_selling_experience": "Yes, regularly",
            "commitment_type_preference": "Recurring",
            "flex_production_capacity": "With some notice",
            "brand_partnership_willingness": "Yes",
            "public_visibility_comfort": "Very comfortable",
            "available_weekly_time": "A few hours a week",
            "upfront_spending_tolerance": "$500 to $2K",
            "risk_tolerance": "Moderate",
            "opportunity_nogo_filters": "Events with less than 200 expected attendees or >100 miles distance",
            "ideal_partner_types": "Local breweries, festival organizers, corporate campus managers",
            "win_definition_90_days": "Secure 2 recurring weekly brewery popup slots and 3 corporate catering gigs.",
            "growth_focus_stage": "Actively growing",
            "stretch_opportunity_permission": "Yes, show me those",
            "opportunity_surfacing_frequency": "Only strong matches"
        },
        "section_11_strategic_goals": {
            "goals_12_month": "Increase net margins to 20% and expand municipal / commercial trenchless sewer contracts.",
            "goals_3_year": "Scale fleet to 12 vans and establish dedicated commercial maintenance division.",
            "long_term_vision": "Premier regional trade contractor across Central Ohio.",
            "exit_strategy": "Pass on to key operator or sell brand to hospitality group in 8-10 years."
        },
        "section_12_pricing_and_revenue": {
            "pricing_method": [
                "Hourly",
                "Per job"
            ],
            "typical_order_size": "$485 service call / $18,500 trenchless project",
            "discounts_and_promotions": "10% discount on recurring corporate weekly bookings.",
            "customer_payment_methods": [
                "Upfront",
                "Net-30",
                "On delivery"
            ]
        },
        "section_13_hiring_and_team_structure": {
            "team_roles": "Master Plumber, Dispatch Manager, Senior HVAC Tech, Journeymen, Apprentices",
            "planning_to_hire_12_months": "Yes",
            "recruitment_channels": [
                "Referrals",
                "Social media",
                "Job boards"
            ],
            "uses_contractors_freelancers": "Sometimes"
        },
        "section_14_sales_and_marketing": {
            "sales_channels": [
                "Word of mouth",
                "Referrals",
                "Social media",
                "Ads"
            ],
            "delivery_methods": [
                "In-person",
                "Phone"
            ],
            "tracks_leads_crm": "Spreadsheet",
            "lead_conversion_rate": "35%",
            "monthly_marketing_budget": "1800"
        },
        "section_15_owner_goals_and_preferences": {
            "current_primary_focus": [
                "Profit",
                "Growth"
            ],
            "day_to_day_involvement": "Very involved",
            "financial_risk_tolerance": "Moderate"
        }
    },

    # 7. OPPORTUNITIES V2 PAYLOAD
    "opportunities": {
        "kpis": {
            "active_opportunities": {"count": 7, "descriptor": "Browse contractor matches"},
            "new_this_week": {"count": 2, "label": "2 new this week"},
            "total_potential_value": "$54,500",
            "avg_fit_score": 91,
            "event_readiness_index": 89,
            "historical_roi": {"multiplier": "3.1x", "sample_size": 5}
        },
        "recommended_hero": {
            "id": "opp_service_hero",
            "type": "Contract RFP",
            "box_type": "Direct Match",
            "out_box": False,
            "title": "Columbus Municipal Housing Trenchless Pipe Replacement Contract",
            "source": "City of Columbus Procurement",
            "match_score": 94,
            "readiness_score": 90,
            "data_trust_indicator": "Verified",
            "risk_level": "Low",
            "drive_time_minutes": 12,
            "distance_miles": 4.5,
            "expires_at": "Closes in 18 days",
            "estimated_revenue": "$36,000 project",
            "listed_fee": "$0 (Public RFP)",
            "why_reason_codes": ["Matches certified trenchless camera crew capacity"],
            "risk_signals": ["Requires 5% bid bond deposit"],
            "verify_flag": False,
            "verify_flag_message": None,
            "registration_url": "https://columbus.gov/procurement/rfp-plumbing",
            "source_url": "https://columbus.gov/bids"
        },
        "more_matches": [],
        "recommended": [
            {
                "id": "opp_service_1",
                "title": "Trenchless Pipe Camera Utilization",
                "impact": "+$18,500 average ticket",
                "strategic_fit": "High-margin specialized service expansion",
                "execution_steps": [
                    "Target residential neighborhoods with homes older than 35 years",
                    "Offer free video camera inspection with any main drain clearing"
                ],
                "risk_rating": "Low"
            }
        ],
        "selected_tracked": [
            {
                "id": "track_service_1",
                "title": "Columbus Municipal Housing Trenchless Pipe Contract",
                "type": "Contract RFP",
                "status": "Tracked",
                "estimated_revenue": "$36,000",
                "next_checkpoint": "Day 2 check-in tomorrow"
            }
        ],
        "portfolio_summary": {
            "active_count": 1,
            "past_count": 5,
            "total_committed_dollars": "$36,000"
        }
    },

    # 8. SCENARIOS PAYLOAD
    "scenarios": {
        "scenario_id": "scen_service_trenchless",
        "confidence": 91,
        "risk": "Low",
        "impact_cards": [
            {"label": "Project Contract Inflow", "value": "+$36,000", "direction": "up"},
            {"label": "Net Margin Boost", "value": "+3.2%", "direction": "up"},
            {"label": "Cash Runway Extension", "value": "+3.8 Months", "direction": "up"}
        ]
    }
}
