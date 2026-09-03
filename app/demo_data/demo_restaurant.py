# backend/app/demo_data/demo_restaurant.py
"""
Complete spec-compliant demo payload for Business #1: Tony's Brooklyn Pizza (demo-restaurant).
Follows exact FA V6 schemas (DASHBOARD MODE, INSIGHTS MODE, DRAWER MODE), Demand Forecast (v9 Split), Business Health, 16-section Business Profile, Opportunities V2 (Research Scout V3.1), and Scenario Lab.
"""

TONYS_BROOKLYN_PIZZA_PAYLOADS = {
    "account": {
        "login_label": "demo-restaurant",
        "business_name": "Tony's Brooklyn Pizza",
        "email": "demo-restaurant@lightsignal.app",
        "industry": "Pizzeria / Restaurant",
        "owner": "Tony Marchetti",
        "is_demo": True,
    },
    
    # 1. DASHBOARD MODE PAYLOAD
    "dashboard": {
        "summary": "Tony's Brooklyn Pizza gross revenue is $88,300 MTD. Food cost drift in cheese (+14%) is compressing net margin to 13.2%.",
        "kpis": {
            "revenue_mtd": {"value": 88300.0, "prior_value": 85100.0, "format_type": "currency", "link": "/overview#revenue"},
            "net_margin_pct": {"value": 0.132, "prior_value": 0.156, "format_type": "percentage", "link": "/overview#margin"},
            "cash": {"value": 75000.0, "prior_value": 72400.0, "format_type": "currency", "link": "/overview#cash"},
            "runway_months": {"value": 12.0, "prior_value": 12.5, "format_type": "months", "link": "/overview#runway"},
            "ai_health_score": {"value": 82, "prior_value": 85, "format_type": "score", "link": "/overview#health"},
        },
        "alerts": [
            {
                "severity": "critical",
                "type": "risk",
                "message": "Mozzarella cost +14% expanding food cost to 33.4% of revenue",
                "icon": "🔴"
            },
            {
                "severity": "below_average",
                "type": "warning",
                "message": "Saturday peak oven capacity bottleneck causing check dropouts",
                "icon": "🟡"
            },
            {
                "severity": "above_average",
                "type": "positive",
                "message": "Catering inflow of $6,400 provides strong non-recurring cash bump",
                "icon": "🟢"
            }
        ],
        "insight_pairs": [
            {
                "head": "Mozzarella Vendor Price Compression",
                "problem": "Cheese vendor prices rose +14% over past 4 weeks, driving food cost from 31% to 33.4% and eroding $2,120/mo gross profit.",
                "solution": "Renegotiate wholesale cheese volume pricing with primary distributor or benchmark against secondary Park Slope suppliers."
            },
            {
                "head": "Saturday Night Deck Oven Bottleneck",
                "problem": "Deck ovens reached 100% physical capacity during Fri-Sat 6-9 PM peak, causing an estimated 18% check walk-away loss.",
                "solution": "Cap peak online delivery orders during 7-8 PM window and shift 15% dough prep to late-afternoon staging."
            }
        ],
        "opportunities": [
            {
                "head": "Local Corporate Catering Expansion",
                "body": "Leverage recent $6,400 catering inflow by targeting 12 office buildings in Park Slope for recurring Thursday lunch orders."
            }
        ],
        "what_changed": [
            "Net margin contracted 2.4 percentage points from 15.6% to 13.2% due to ingredient price inflation.",
            "Revenue MTD rose 3.8% vs prior month driven by weekend dine-in volume."
        ],
        "missing_data_notice": None
    },

    # 2. INSIGHTS MODE PAYLOAD
    "insights_mode": {
        "profitability_banner": {
            "status": "below_average",
            "headline": "Profitable overall, but margin tightening from ingredient cost inflation.",
            "supporting_text": "Gross margin at 66.6%, down 2.4 pts vs prior month due to 14% increase in mozzarella COGS.",
            "missing_data_notice": None
        },
        "items": [
            {
                "signal_id": "margin_compression",
                "pressing_score": 85,
                "tier": "tier_1",
                "headline": "Food COGS Drifting Above 33% Threshold",
                "whats_going_on": "Weekly vendor purchases for cheese and specialty flour increased 14% this month, pushing food cost from 31.0% to 33.4% of total revenue ($2,120/mo net profit drag).",
                "why_it_matters_now": "Unchecked ingredient inflation will erode annual cash reserves by over $25,000 if not addressed before Q4 catering season.",
                "what_to_do": "Review dairy supplier contract, audit slice portioning consistency, and consider a modest 50-cent menu adjustment on premium specialty pies.",
                "expected_impact": {
                    "value_text": "+$2.1K/mo margin recovered",
                    "calculation_basis": "Trimming food cost back to 31.0% target on $88,300 monthly volume restores $2,120/mo to net income."
                },
                "effort": "quick_win",
                "confidence": "high",
                "directive": {
                    "shape_id": "waterfall_margin_bridge",
                    "state": "active",
                    "theme": "warning",
                    "numbers": {"base_margin": 69.0, "cogs_impact": -2.4, "current_margin": 66.6},
                    "labels": {"base": "Base Margin", "impact": "Cheese COGS", "current": "Current Margin"}
                }
            },
            {
                "signal_id": "capacity_bottleneck",
                "pressing_score": 72,
                "tier": "tier_1",
                "headline": "Oven Throughput Bottleneck on Weekend Evenings",
                "whats_going_on": "Toast POS data shows 18% check dropout between 6:30 PM and 8:30 PM on Saturdays, matching physical deck oven capacity limits.",
                "why_it_matters_now": "Weekend walk-aways cap monthly top-line growth at $90,000 despite strong local demand.",
                "what_to_do": "Implement delivery order throttling during 7-8 PM peak hours and introduce pre-baked slice staging for counter traffic.",
                "expected_impact": {
                    "value_text": "+$3,400/mo incremental sales",
                    "calculation_basis": "Capturing half of lost peak weekend check walk-aways adds 12 tickets/night at $31 average ticket."
                },
                "effort": "moderate",
                "confidence": "high",
                "directive": {
                    "shape_id": "capacity_utilization_gauge",
                    "state": "active",
                    "theme": "critical",
                    "numbers": {"peak_utilization": 100.0, "lost_checks_pct": 18.0},
                    "labels": {"utilization": "Peak Oven Load", "lost": "Lost Orders"}
                }
            }
        ],
        "missing_data_notice": None
    },

    # 3. DRAWER MODE PAYLOAD
    "drawer_mode": {
        "revenue": {
            "value_text": "$88,300",
            "status_badge": {"label": "Healthy Growth", "severity": "above_average"},
            "headline_read": "Revenue up 3.8% MTD, supported by strong Fri-Sat dine-in volume and $6,400 catering bump.",
            "benchmarks": {
                "peer_avg": "$78,500/mo",
                "sba_metric": "Top 25% of independent NYC pizzerias",
                "position": "above",
                "gap_text": "Outperforming peer average by 12.5%"
            },
            "drivers": [
                {"description": "Dine-in pie sales (62% revenue share)", "impact": "+$54,746", "category": "Core Sales"},
                {"description": "Delivery & takeout orders (23% revenue share)", "impact": "+$20,309", "category": "Delivery"},
                {"description": "Slice counter foot traffic (15% revenue share)", "impact": "+$13,245", "category": "Counter Sales"}
            ],
            "actions": [
                {"description": "Promote catering menu to local corporate accounts for Tuesday-Thursday lunch bookings", "priority": "high", "effort": "quick_win"},
                {"description": "Review peak weekend delivery throttle settings in Toast POS", "priority": "medium", "effort": "quick_win"}
            ]
        }
    },

    # 4. DEMAND FORECAST PAYLOAD
    "demand_forecast": {
        "metrics": {
            "forecast_series": [72400.0, 75000.0, 83800.0, 88300.0, 88300.0, 88300.0, 85600.0, 83800.0, 90000.0, 92700.0, 95300.0, 104200.0]
        },
        "flags": [
            {"severity": "red", "title": "Cheese COGS +14%"},
            {"severity": "amber", "title": "Saturday Oven Capacity Limit"}
        ],
        "data": {
            "historical_revenue": [
                {"date": "2026-01-01", "amount": 72400.0},
                {"date": "2026-02-01", "amount": 75000.0},
                {"date": "2026-03-01", "amount": 83800.0},
                {"date": "2026-04-01", "amount": 88300.0}
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
                        "headline": "Projected weekend revenue of $14,800 across Friday dinner & Saturday rush.",
                        "expected_value": "$14,800",
                        "expected_unit": "revenue",
                        "volume_forecast": 185,
                        "demand_unit": "Covers",
                        "confidence_pct": 92,
                        "confidence_label": "High",
                        "anchor": "Anchored in Toast POS 12-week Friday/Saturday dining room seatings."
                    },
                    "swing_factor": {
                        "headline": "Park Slope Street Festival (+18% foot traffic)",
                        "delta_text": "+$2,400",
                        "direction": "up",
                        "reasoning": "High pedestrian inflow on 5th Ave boosting slice counter walk-ins."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "Order 15 extra dough boxes & schedule 2 additional floor servers", "severity": "above_average"},
                        "whats_moving": {"summary": "2 positive drivers (Festival foot traffic, patio dining weather)", "severity": "above_average"},
                        "breakdown": {"summary": "70% dine-in, 18% takeout, 12% slice counter", "severity": "above_average"},
                        "track_record": {"summary": "Weekend forecast accuracy ran within 2.4% over past 4 weekends", "severity": "above_average"},
                        "world_scan": {"summary": "Clear skies (72°F) expected all Saturday afternoon", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_order_mozz_01",
                            "action": "Order 15 additional mozzarella & dough cases by Thursday 2 PM",
                            "deadline": "Thu, Feb 6",
                            "priority": "high",
                            "tied_to_driver": "Park Slope Street Festival",
                            "why_this_much": "Prevents dough stockouts during Saturday 7-9 PM peak.",
                            "dollar_logic": "Secures +$2,400 in incremental high-margin pie sales."
                        }
                    ],
                    "whats_moving": [
                        {
                            "name": "Park Slope Street Festival",
                            "window": "This Weekend",
                            "severity": "green",
                            "impact_text": "+$2,400",
                            "reasoning": "Annual street fair draws 4,000+ local visitors within 2 blocks.",
                            "source": "Local Event Calendar",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 8500.0,
                        "expected_losses": 400.0,
                        "unbooked_demand": 6700.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Weekend predictions hit within 2.4% over last month.",
                        "lean_guidance": "Slight upward bias on warm sunny Saturdays."
                    },
                    "world_scan": [
                        {
                            "flag": "5th Ave Street Fair Closure",
                            "horizon": "Saturday 10 AM - 8 PM",
                            "depends_on": "Pedestrian patio seating & slice counter",
                            "action_yet": "Set up outdoor slice warmer booth",
                            "source": "City Permits Registry"
                        }
                    ]
                },
                {
                    "window": "Next 30 Days",
                    "severity": "amber",
                    "hero": {
                        "eyebrow": "Forward Demand Read",
                        "headline": "Monthly demand tracking at $88,300 MTD with strong weekend dine-in volume.",
                        "expected_value": "$88,300",
                        "expected_unit": "revenue",
                        "confidence_pct": 88,
                        "confidence_label": "High",
                        "anchor": "Anchored in 3-year same-month Toast POS actuals + Park Slope neighborhood foot traffic."
                    },
                    "swing_factor": {
                        "headline": "Mozzarella supplier price drift (+14%)",
                        "delta_text": "-$2,120",
                        "direction": "down",
                        "reasoning": "Ingredient inflation driving food cost from 31% to 33.4% of total revenue."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "2 operational actions to protect weekend margin and oven capacity", "severity": "below_average"},
                        "whats_moving": {"summary": "3 key demand drivers (dine-in pie sales, catering inflow, slice counter)", "severity": "above_average"},
                        "breakdown": {"summary": "62% dine-in, 23% delivery, 15% counter slice sales", "severity": "above_average"},
                        "track_record": {"summary": "Prior 90-day forecast ran within 3.8% of Toast POS actuals", "severity": "above_average"},
                        "world_scan": {"summary": "Park Slope foot traffic steady; local office catering demand rising", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_tony_1",
                            "title": "Renegotiate wholesale cheese contract with primary distributor",
                            "deadline": "Feb 15",
                            "priority": "high",
                            "tied_to_driver": "Cheese Inflation",
                            "why_this_much": "Protects $2,120/mo gross profit by restoring food cost to 31% target.",
                            "dollar_logic": "+$2,120/mo recovered margin"
                        },
                        {
                            "id": "act_tony_2",
                            "title": "Cap peak online delivery slots on Toast POS during 7-8 PM window",
                            "deadline": "Immediate",
                            "priority": "medium",
                            "tied_to_driver": "Deck Oven Bottleneck",
                            "why_this_much": "Prevents 18% check walk-aways on Saturday peak hours.",
                            "dollar_logic": "+$3,400/mo incremental sales"
                        }
                    ],
                    "drivers": [
                        {
                            "name": "Cheese Inflation",
                            "severity": "red",
                            "window": "Next 30 Days",
                            "impact_text": "-$2,120",
                            "reasoning": "14% price increase from primary dairy vendor.",
                            "source": "Vendor Invoices",
                            "confidence": "high"
                        },
                        {
                            "name": "Deck Oven Bottleneck",
                            "severity": "amber",
                            "window": "Next 30 Days",
                            "impact_text": "-$3,400",
                            "reasoning": "Physical oven throughput reached 100% capacity Sat 6-9 PM.",
                            "source": "Toast POS Checks",
                            "confidence": "high"
                        },
                        {
                            "name": "Corporate Catering Inflow",
                            "severity": "green",
                            "window": "Next 30 Days",
                            "impact_text": "+$6,400",
                            "reasoning": "One-time weekday catering bookings in Park Slope.",
                            "source": "Direct Bookings",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 54746.0,
                        "expected_losses": 2120.0,
                        "unbooked_demand": 33554.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Forecast accuracy ran within 3.8% of actual Toast POS sales over the last quarter.",
                        "lean_guidance": "Slight conservative bias on rainy Friday night takeout volume."
                    },
                    "world_scan": [
                        {
                            "flag": "Park Slope Neighborhood Office Density",
                            "horizon": "Feb-Mar",
                            "depends_on": "Weekday lunch catering demand",
                            "action_yet": "Distribute corporate catering menus to 12 target office buildings",
                            "source": "Local Market Scan"
                        }
                    ]
                }
            ]
        }
    },

    # 5. BUSINESS HEALTH PAYLOAD
    "business_health": {
        "overall_score": 82,
        "status": "Healthy",
        "dimensions": {
            "liquidity": {"score": 88, "label": "Strong", "cash_months": 12.0},
            "profitability": {"score": 75, "label": "Moderate", "net_margin": 13.2},
            "growth": {"score": 84, "label": "Steady", "yoy_growth": 4.2},
            "efficiency": {"score": 79, "label": "Good", "table_turnover": "3.8x"},
            "resilience": {"score": 85, "label": "High", "debt_load": "$0 (No Loan)"}
        }
    },

    # 6. BUSINESS PROFILE PAYLOAD
    "business_profile": {
        "section_01_business_basics": {
            "business_name": "Tony's Brooklyn Pizza",
            "headquarters": "Park Slope, Brooklyn, NY",
            "years_in_business": "More than 10 years",
            "timezone": "America/New_York",
            "currency": "USD",
            "legal_entity_type": "LLC",
            "ein": "11-2345678",
            "locations": [
                {
                    "name": "Tony's Brooklyn Pizza - Flagship",
                    "address": "284 5th Ave, Brooklyn, NY 11215",
                    "role": "Primary Restaurant",
                    "status": "active"
                }
            ]
        },
        "section_02_ownership_and_key_people": {
            "ownership_breakdown": "Tony Marchetti (100%)",
            "decision_maker": "Tony Marchetti, Founder & Head Pizzaiolo",
            "bookkeeper_financial_handler": "Brooklyn CPA Partners (External)",
            "has_backup_operator": "Yes"
        },
        "section_03_industry_and_model": {
            "business_description": "Artisanal deck-oven NY style pizzeria serving dine-in, takeout, and corporate catering in Park Slope.",
            "revenue_model_description": "Direct food sales at events, counter orders, catering orders, and delivery.",
            "target_market_type": "Both",
            "business_stage": "Growing and adding capacity"
        },
        "section_04_operations": {
            "team_size": "Small team of 4 to 10",
            "payroll_type": "Mostly employees with some contractors",
            "operating_hours": "Tue-Sun, 11:30am-10pm",
            "growth_limiters": [
                "Staff",
                "Equipment",
                "Time"
            ],
            "single_supplier_dependency": "We have key suppliers but alternatives exist",
            "uses_pos_system": "Yes",
            "space_ownership_status": "Lease it",
            "operational_software": [
                "Booking or reservation system",
                "Payroll software",
                "Inventory management"
            ],
            "recent_supplier_issues": "No",
            "critical_materials_inputs": "Whole milk low-moisture mozzarella, San Marzano tomatoes, high-gluten flour."
        },
        "section_05_financial_overview": {
            "accounting_system": "QuickBooks",
            "connect_accounting_now": "Yes",
            "fiscal_year_start": "January to December (all 12 months)",
            "banks_and_lenders": "First Local Bank",
            "business_loan_history": "Yes and paid it off"
        },
        "section_06_assets_and_equipment": {
            "major_assets": "3x Marsal Deck Ovens, Hobart 60qt Dough Mixer, Walk-in Cooler, Ram ProMaster Van",
            "asset_ownership_status": "Truck is leased, internal equipment is owned",
            "asset_purchase_dates": "Ovens bought Mar 2018, van leased Jan 2021",
            "asset_condition": "Good working condition, regular maintenance performed",
            "leased_monthly_payment": "$500 to $2K"
        },
        "section_07_customers_and_market": {
            "customer_distance": "Across the metro",
            "strongest_seasons": [
                "Fall",
                "Winter",
                "Spring"
            ],
            "customer_acquisition_channels": [
                "Walk-by / drive-by",
                "Word of mouth",
                "Social media",
                "Repeat regulars"
            ],
            "typical_customers_description": "Park Slope families, downtown lunch workers, and local corporate offices ordering catering.",
            "monthly_customer_volume": "2850",
            "repeat_business_rate": "High",
            "target_customer_types": "Corporate offices looking for weekly lunch catering.",
            "customer_concentration": "No, spread across many",
            "seasonality_level": "A little seasonal",
            "customer_geographic_source": "Within 10–15 miles",
            "opportunity_radius_miles": "25",
            "max_travel_distance_miles": "75",
            "local_opportunity_preference": "Open to nearby areas if high-value",
            "geographic_service_areas": "Park Slope, Gowanus, Prospect Heights, Downtown Brooklyn",
            "weather_impact": "High"
        },
        "section_08_risk_and_exposure": {
            "carries_business_insurance": "Yes",
            "critical_dependencies": "Local commissary kitchen and primary cheese distributor.",
            "revenue_concentration": "No, spread across many",
            "active_permits_licenses": "NYC Dept of Health Permit, City Business License, ServSafe",
            "in_progress_permits_licenses": "Sidewalk cafe temporary renewal permit",
            "local_operating_restrictions": "Designated food zones, noise ordinances after 10 PM"
        },
        "section_09_capacity_and_constraints": {
            "monthly_customer_capacity": "3200",
            "could_handle_more_capacity": "Yes, we had plenty of room",
            "current_busy_level": [
                "Around capacity"
            ],
            "operational_slowdown_factors": [
                "Labor",
                "Equipment"
            ],
            "has_active_business_financing": "No"
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
            "goals_12_month": "Increase net margins to 20% and scale corporate lunch catering orders.",
            "goals_3_year": "Add a second food truck or satellite hub and expand into neighboring areas.",
            "long_term_vision": "Build a recognized regional mobile and storefront catering brand.",
            "exit_strategy": "Pass on to key operator or sell brand to hospitality group in 8-10 years."
        },
        "section_12_pricing_and_revenue": {
            "pricing_method": [
                "Per unit",
                "Per job"
            ],
            "typical_order_size": "$31 retail / $380 catering",
            "discounts_and_promotions": "10% discount on recurring corporate weekly bookings.",
            "customer_payment_methods": [
                "Upfront",
                "On delivery"
            ]
        },
        "section_13_hiring_and_team_structure": {
            "team_roles": "Head Pizzaiolo, Prep Cook, Cashier/Server, Driver",
            "planning_to_hire_12_months": "Yes",
            "recruitment_channels": [
                "Referrals",
                "Social media",
                "Walk-ins"
            ],
            "uses_contractors_freelancers": "Sometimes"
        },
        "section_14_sales_and_marketing": {
            "sales_channels": [
                "Word of mouth",
                "Social media",
                "Events"
            ],
            "delivery_methods": [
                "In-person",
                "Online",
                "Delivery"
            ],
            "tracks_leads_crm": "Spreadsheet",
            "lead_conversion_rate": "35%",
            "monthly_marketing_budget": "650"
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

    # 7. OPPORTUNITIES V2 PAYLOAD (Full Research Scout V3.1 Spec)
    "opportunities": {
        "kpis": {
            "active_opportunities": {"count": 8, "descriptor": "Browse all matches"},
            "new_this_week": {"count": 2, "label": "2 new this week"},
            "total_potential_value": "$28,520",
            "avg_fit_score": 88,
            "event_readiness_index": 85,
            "historical_roi": {"multiplier": "2.4x", "sample_size": 4}
        },
        "recommended_hero": {
            "id": "opp_tony_hero",
            "type": "Catering Program",
            "box_type": "Direct Match",
            "out_box": False,
            "title": "Park Slope Corporate Lunch Catering Expansion",
            "source": "NYC Corporate Dining Network",
            "match_score": 92,
            "readiness_score": 88,
            "data_trust_indicator": "Verified",
            "risk_level": "Low",
            "drive_time_minutes": 10,
            "distance_miles": 1.2,
            "expires_at": "Closes in 14 days",
            "estimated_revenue": "$6,400/mo",
            "listed_fee": "$0 (Direct Contract)",
            "why_reason_codes": [
                "Utilizes existing kitchen line downtime during Tuesday-Thursday 11 AM - 2 PM window",
                "Toast POS indicates $6.4K high-margin catering capacity available without equipment expansion"
            ],
            "risk_signals": [
                "Requires dedicated delivery driver during Thursday noon rush"
            ],
            "verify_flag": False,
            "verify_flag_message": None,
            "registration_url": "https://tonysbrooklynpizza.com/catering-partner",
            "source_url": "https://nyccorporatedining.org/listings/park-slope-catering"
        },
        "more_matches": [
            {
                "id": "opp_tony_strip_1",
                "type": "Vendor Program",
                "box_type": "Out-of-box",
                "out_box": True,
                "title": "Brooklyn Artisan Food Festival Catering Spot",
                "source": "Brooklyn Chamber of Commerce",
                "match_score": 84,
                "readiness_score": 80,
                "data_trust_indicator": "Verified",
                "risk_level": "Low",
                "drive_time_minutes": 15,
                "distance_miles": 2.5,
                "expires_at": "Closes in 21 days",
                "estimated_revenue": "$4,200 weekend",
                "listed_fee": "$350 booth fee",
                "why_reason_codes": ["Leverages slice counter popularity for festival foot traffic"],
                "risk_signals": ["Weather risk: Outdoor event"],
                "verify_flag": False,
                "verify_flag_message": None,
                "registration_url": "https://brooklynchamber.com/vendor-apply",
                "source_url": "https://brooklynchamber.com/events"
            }
        ],
        "recommended": [
            {
                "id": "opp_tony_1",
                "title": "Park Slope Corporate Lunch Catering Expansion",
                "impact": "+$6,400/mo net revenue",
                "strategic_fit": "Fits mid-week kitchen downtime perfectly",
                "execution_steps": [
                    "Distribute corporate catering menus to 12 office buildings within 1 mile",
                    "Offer 10% discount on recurring Tuesday-Thursday lunch orders"
                ],
                "risk_rating": "Low"
            },
            {
                "id": "opp_tony_2",
                "title": "Dairy Wholesale Direct Renegotiation",
                "impact": "+$2,120/mo cost savings",
                "strategic_fit": "Recovers food cost drift back to 31% target",
                "execution_steps": [
                    "Benchmark cheese pricing against secondary Brooklyn suppliers",
                    "Lock in quarterly volume commitments for mozzarella"
                ],
                "risk_rating": "Low"
            }
        ],
        "selected_tracked": [
            {
                "id": "track_1",
                "title": "Park Slope Corporate Lunch Catering Expansion",
                "type": "Catering Program",
                "status": "Tracked",
                "estimated_revenue": "$6,400/mo",
                "next_checkpoint": "Day 3 check-in in 2 days"
            }
        ],
        "portfolio_summary": {
            "active_count": 2,
            "past_count": 4,
            "total_committed_dollars": "$18,500"
        }
    },

    # 8. SCENARIOS PAYLOAD
    "scenarios": {
        "scenario_id": "scen_tony_catering",
        "confidence": 88,
        "risk": "Low",
        "impact_cards": [
            {"label": "Monthly Revenue Lift", "value": "+$6,400", "direction": "up"},
            {"label": "Net Margin Impact", "value": "+1.8%", "direction": "up"},
            {"label": "Cash Runway Addition", "value": "+1.5 Months", "direction": "up"}
        ]
    }
}
