# backend/app/demo_data/demo_salon.py
"""
Complete spec-compliant demo payload for Business #4: Velvet & Vine Salon (demo-salon).
Follows exact FA V6 schemas (DASHBOARD MODE, INSIGHTS MODE, DRAWER MODE), Demand Forecast (v9 Split), Business Health, 16-section Business Profile, Opportunities V2 (Research Scout V3.1), and Scenario Lab.
"""

VELVET_VINE_SALON_PAYLOADS = {
    "account": {
        "login_label": "demo-salon",
        "business_name": "Velvet & Vine Salon",
        "email": "demo-salon@lightsignal.app",
        "industry": "Hair Salon & Personal Care",
        "owner": "Priya Raman",
        "is_demo": True,
    },
    
    # 1. DASHBOARD MODE PAYLOAD
    "dashboard": {
        "summary": "Velvet & Vine monthly revenue is $40,500 MTD. Senior colorist absence reduced peak weekend salon chair volume by 22%.",
        "kpis": {
            "revenue_mtd": {"value": 40500.0, "prior_value": 42100.0, "format_type": "currency", "link": "/overview#revenue"},
            "net_margin_pct": {"value": 0.162, "prior_value": 0.185, "format_type": "percentage", "link": "/overview#margin"},
            "cash": {"value": 36200.0, "prior_value": 38500.0, "format_type": "currency", "link": "/overview#cash"},
            "runway_months": {"value": 8.5, "prior_value": 9.1, "format_type": "months", "link": "/overview#runway"},
            "ai_health_score": {"value": 80, "prior_value": 84, "format_type": "score", "link": "/overview#health"},
        },
        "alerts": [
            {
                "severity": "critical",
                "type": "risk",
                "message": "Appointment no-show rate doubled from 4% to 11% ($1,850/mo lost revenue)",
                "icon": "🔴"
            },
            {
                "severity": "below_average",
                "type": "warning",
                "message": "Senior colorist leave caused 22% drop in Thu-Sat chair utilization",
                "icon": "🟡"
            },
            {
                "severity": "above_average",
                "type": "positive",
                "message": "Retail hair product attach rate increased from 8% to 13% ($1,400 bump)",
                "icon": "🟢"
            }
        ],
        "insight_pairs": [
            {
                "head": "Appointment No-Show Leaky Revenue",
                "problem": "Unconfirmed appointment no-shows doubled from 4% to 11% this month, causing $1,850 in unbooked high-value color hours.",
                "solution": "Require a 30% credit card deposit on all color appointments over $100 and activate automated SMS reminders 24 hours prior."
            },
            {
                "head": "Mid-Week Tuesday-Wednesday Utilization Gap",
                "problem": "Tue-Wed salon chair utilization sits at 55% compared to 95% weekend saturation, leaving 18 hours of unbooked chair time weekly.",
                "solution": "Launch a 'Mid-Week Gloss & Blowout' package for local subscribers to boost Tuesday-Wednesday booking density."
            }
        ],
        "opportunities": [
            {
                "head": "Bridal Package & Retail Cross-Sell",
                "body": "Expand retail product bundles to bridal parties to increase retail revenue share toward the 12% annual target."
            }
        ],
        "what_changed": [
            "Chair utilization on Thu-Sat dipped 22% during key-person 2-week leave.",
            "Retail attach rate rose to 13% following front-desk push."
        ],
        "missing_data_notice": None
    },

    # 2. INSIGHTS MODE PAYLOAD
    "insights_mode": {
        "profitability_banner": {
            "status": "above_average",
            "headline": "Solid core performance; appointment deposit policy will reclaim leaky revenue.",
            "supporting_text": "Service gross margin holds at 55.0% after commission; retail attach push generated $1,400 incremental income.",
            "missing_data_notice": None
        },
        "items": [
            {
                "signal_id": "no_show_leakage",
                "pressing_score": 83,
                "tier": "tier_1",
                "headline": "No-Show Rate Rose to 11% ($1,850/mo Leaky Revenue)",
                "whats_going_on": "Square Appointments tracking shows uncancelled no-shows doubled from 4.0% to 11.0% over the last 3 weeks, leaving prime weekend color slots empty.",
                "why_it_matters_now": "At an average ticket of $145 for color services, unbooked empty slots directly reduce monthly salon take.",
                "what_to_do": "Implement a 30% booking deposit policy for appointments >$100 via Square Appointments and enable 24h SMS confirmation prompts.",
                "expected_impact": {
                    "value_text": "+$1,850/mo recovered",
                    "calculation_basis": "Reducing no-shows back to the 4% baseline reclaims ~13 high-value color appointments monthly."
                },
                "effort": "quick_win",
                "confidence": "high",
                "directive": {
                    "shape_id": "no_show_rate_chart",
                    "state": "active",
                    "theme": "critical",
                    "numbers": {"baseline_pct": 4.0, "current_pct": 11.0, "target_pct": 4.0},
                    "labels": {"baseline": "Normal Rate", "current": "Current Spike", "target": "Target Policy"}
                }
            }
        ],
        "missing_data_notice": None
    },

    # 3. DRAWER MODE PAYLOAD
    "drawer_mode": {
        "revenue": {
            "value_text": "$40,500",
            "status_badge": {"label": "Steady Booking", "severity": "above_average"},
            "headline_read": "Revenue holds at $40.5K MTD; 92% hair services, 8% retail product attach.",
            "benchmarks": {
                "peer_avg": "$36,000/mo",
                "sba_metric": "Top performance for Chicago boutique salons",
                "position": "above",
                "gap_text": "12.5% ahead of regional salon benchmark"
            },
            "drivers": [
                {"description": "Hair color & styling services (92% share)", "impact": "+$37,260", "category": "Service Revenue"},
                {"description": "Retail hair product sales (8% share)", "impact": "+$3,240", "category": "Retail Attach"}
            ],
            "actions": [
                {"description": "Enable 30% deposit requirement on Square Appointments for color services", "priority": "high", "effort": "quick_win"}
            ]
        }
    },

    # 4. DEMAND FORECAST PAYLOAD
    "demand_forecast": {
        "metrics": {
            "forecast_series": [34425.0, 36450.0, 38475.0, 40500.0, 46575.0, 42525.0, 38475.0, 38475.0, 40500.0, 40500.0, 42525.0, 46575.0]
        },
        "flags": [
            {"severity": "red", "title": "No-Show Rate Doubled to 11%"},
            {"severity": "amber", "title": "Senior Colorist Leave Capacity Drop"}
        ],
        "data": {
            "historical_revenue": [
                {"date": "2026-01-01", "amount": 34425.0},
                {"date": "2026-02-01", "amount": 36450.0},
                {"date": "2026-03-01", "amount": 38475.0},
                {"date": "2026-04-01", "amount": 40500.0}
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
                        "headline": "Projected weekend salon revenue of $6,800 with 94% chair utilization.",
                        "expected_value": "$6,800",
                        "expected_unit": "revenue",
                        "volume_forecast": 42,
                        "demand_unit": "Appointments",
                        "confidence_pct": 91,
                        "confidence_label": "High",
                        "anchor": "Anchored in 68% client rebooking rate + Boulevard salon booking engine."
                    },
                    "swing_factor": {
                        "headline": "Bridal party group booking (+3 chairs)",
                        "delta_text": "+$1,200",
                        "direction": "up",
                        "reasoning": "High-margin color & blowout package booked for Saturday morning."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "Enable $25 deposit policy for Saturday color appointments", "severity": "above_average"},
                        "whats_moving": {"summary": "2 positive drivers (Bridal group booking, Prom season prep)", "severity": "above_average"},
                        "breakdown": {"summary": "72% color/balayage, 20% haircuts, 8% retail products", "severity": "above_average"},
                        "track_record": {"summary": "Weekend forecast accuracy ran within 2.1% over last 30 days", "severity": "above_average"},
                        "world_scan": {"summary": "Local prom event driving Friday afternoon blowout demand", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_salon_dep_01",
                            "action": "Enable $25 deposit requirement on Boulevard for Saturday color appointments",
                            "deadline": "Fri, Feb 7",
                            "priority": "high",
                            "tied_to_driver": "Bridal party group booking",
                            "why_this_much": "Protects chair capacity against last-minute no-shows.",
                            "dollar_logic": "Recovers ~$950 in lost chair revenue."
                        }
                    ],
                    "whats_moving": [
                        {
                            "name": "Bridal party group booking",
                            "window": "This Weekend",
                            "severity": "green",
                            "impact_text": "+$1,200",
                            "reasoning": "Full bridal party styling reserved across 3 senior stylists.",
                            "source": "Boulevard Booking Engine",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 5200.0,
                        "expected_losses": 250.0,
                        "unbooked_demand": 1850.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Salon weekend forecasts hit within 2.1% accuracy.",
                        "lean_guidance": "Consistent high rebooking accuracy on weekend slots."
                    },
                    "world_scan": [
                        {
                            "flag": "Regional High School Prom Gala",
                            "horizon": "Friday 3 PM - 7 PM",
                            "depends_on": "Blowout chair availability",
                            "action_yet": "Add 2 express blowout slots",
                            "source": "Local Events Register"
                        }
                    ]
                },
                {
                    "window": "Next 30 Days",
                    "severity": "amber",
                    "hero": {
                        "eyebrow": "Forward Demand Read",
                        "headline": "Salon appointment demand tracking steady at $40,500 MTD; deposit policy will reclaim leaky revenue.",
                        "expected_value": "$40,500",
                        "expected_unit": "revenue",
                        "confidence_pct": 87,
                        "confidence_label": "High",
                        "anchor": "Anchored in Square Appointments rebooking history + 68% client retention rate."
                    },
                    "swing_factor": {
                        "headline": "Unconfirmed appointment no-show spike (11% rate)",
                        "delta_text": "-$1,850",
                        "direction": "down",
                        "reasoning": "No-show rate doubled from 4.0% to 11.0% during key weekend color slots."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "2 actions to mandate booking deposits and fill Tuesday-Wednesday chair slots", "severity": "below_average"},
                        "whats_moving": {"summary": "3 appointment drivers (hair color, styling services, retail attach)", "severity": "above_average"},
                        "breakdown": {"summary": "92% service booking, 8% retail product attach", "severity": "above_average"},
                        "track_record": {"summary": "Prior 90-day forecast ran within 3.2% of Square Appointments actuals", "severity": "above_average"},
                        "world_scan": {"summary": "Chicago Logan Square local beauty & wedding demand tracking high", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_salon_1",
                            "title": "Enable 30% credit card deposit requirement on Square Appointments for color services",
                            "deadline": "Feb 10",
                            "priority": "high",
                            "tied_to_driver": "No-Show Spike",
                            "why_this_much": "Reclaims $1,850/mo lost to unconfirmed appointment cancellations.",
                            "dollar_logic": "+$1,850/mo recovered revenue"
                        },
                        {
                            "id": "act_salon_2",
                            "title": "Launch 'Mid-Week Gloss & Blowout' package for Tuesday-Wednesday booking",
                            "deadline": "Feb 20",
                            "priority": "medium",
                            "tied_to_driver": "Mid-Week Utilization Gap",
                            "why_this_much": "Lifts mid-week chair utilization from 55% to 70% target.",
                            "dollar_logic": "+$2,200/mo incremental sales"
                        }
                    ],
                    "drivers": [
                        {
                            "name": "No-Show Spike",
                            "severity": "red",
                            "window": "Next 30 Days",
                            "impact_text": "-$1,850",
                            "reasoning": "Unconfirmed cancellations doubled to 11%.",
                            "source": "Square Appointments",
                            "confidence": "high"
                        },
                        {
                            "name": "Key-Person Colorist Leave",
                            "severity": "amber",
                            "window": "Next 30 Days",
                            "impact_text": "-$2,400",
                            "reasoning": "Senior colorist out for 2 weeks during peak Thu-Sat hours.",
                            "source": "Salon Schedule",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 37260.0,
                        "expected_losses": 1850.0,
                        "unbooked_demand": 5090.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Prior 90-day forecast ran within 3.2% of actual Square Appointments revenue.",
                        "lean_guidance": "Slight conservative bias on retail hair product add-on purchases."
                    },
                    "world_scan": [
                        {
                            "flag": "Chicago Logan Square Spring Prom & Wedding Season",
                            "horizon": "May",
                            "depends_on": "Bridal party package inquiries",
                            "action_yet": "Promote bridal packages on Instagram and email newsletter",
                            "source": "Local Event & Social Scan"
                        }
                    ]
                }
            ]
        }
    },

    # 5. BUSINESS HEALTH PAYLOAD
    "business_health": {
        "overall_score": 80,
        "status": "Healthy",
        "dimensions": {
            "liquidity": {"score": 82, "label": "Strong", "cash_months": 8.5},
            "profitability": {"score": 78, "label": "Good", "net_margin": 16.2},
            "growth": {"score": 81, "label": "Steady", "yoy_growth": 4.5},
            "efficiency": {"score": 74, "label": "Moderate", "chair_utilization": "68%"},
            "resilience": {"score": 85, "label": "High", "debt_load": "$0 (No Debt)"}
        }
    },

    # 6. BUSINESS PROFILE PAYLOAD
    "business_profile": {
        "section_01_business_basics": {
            "business_name": "Velvet & Vine Salon",
            "headquarters": "Chicago, IL (Logan Square)",
            "years_in_business": "5 to 10 years",
            "timezone": "America/Chicago",
            "currency": "USD",
            "legal_entity_type": "LLC",
            "ein": "36-5432109",
            "locations": [
                {
                    "name": "Velvet & Vine Studio",
                    "address": "2518 N Milwaukee Ave, Chicago, IL 60647",
                    "role": "Primary Studio",
                    "status": "active"
                }
            ]
        },
        "section_02_ownership_and_key_people": {
            "ownership_breakdown": "Priya Raman (100%)",
            "decision_maker": "Priya Raman, Founder & Creative Director",
            "bookkeeper_financial_handler": "Windy City CPA Associates (External)",
            "has_backup_operator": "Yes"
        },
        "section_03_industry_and_model": {
            "business_description": "High-end boutique hair salon and organic scalp therapy studio offering balayage, precision cutting, and bridal hair styling.",
            "revenue_model_description": "In-salon service appointments, retail organic hair products, and bridal package bookings.",
            "target_market_type": "Both",
            "business_stage": "Growing and adding capacity"
        },
        "section_04_operations": {
            "team_size": "Small team of 4 to 10",
            "payroll_type": "Mostly employees with some contractors",
            "operating_hours": "Tue-Sat 10am-8pm, Sun-Mon Closed",
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
                "Scheduling software",
                "Payroll software"
            ],
            "recent_supplier_issues": "No",
            "critical_materials_inputs": "Organic hair color formulations, salon treatment tonics, high-end styling tools."
        },
        "section_05_financial_overview": {
            "accounting_system": "QuickBooks",
            "connect_accounting_now": "Yes",
            "fiscal_year_start": "January to December (all 12 months)",
            "banks_and_lenders": "First Local Bank",
            "business_loan_history": "Yes and paid it off"
        },
        "section_06_assets_and_equipment": {
            "major_assets": "8x Belvedere Styling Chairs, 3x Shampoo Backwash Units, Takara Belmont Wash Stations",
            "asset_ownership_status": "Truck is leased, internal equipment is owned",
            "asset_purchase_dates": "Studio buildout 2019, wash stations refreshed 2022",
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
                "Walk-by / drive-by",
                "Word of mouth",
                "Social media",
                "Repeat regulars"
            ],
            "typical_customers_description": "Urban professionals, neighborhood residents, and regional brides seeking specialty organic color and styling.",
            "monthly_customer_volume": "280",
            "repeat_business_rate": "High",
            "target_customer_types": "Corporate offices looking for weekly lunch catering.",
            "customer_concentration": "No, spread across many",
            "seasonality_level": "A little seasonal",
            "customer_geographic_source": "Within 10–15 miles",
            "opportunity_radius_miles": "25",
            "max_travel_distance_miles": "75",
            "local_opportunity_preference": "Open to nearby areas if high-value",
            "geographic_service_areas": "Logan Square, Wicker Park, Bucktown, and Greater Chicago",
            "weather_impact": "High"
        },
        "section_08_risk_and_exposure": {
            "carries_business_insurance": "Yes",
            "critical_dependencies": "Licensed master cosmetologists and organic color supply availability",
            "revenue_concentration": "No, spread across many",
            "active_permits_licenses": "Illinois Cosmetology Salon License, City of Chicago Business License",
            "in_progress_permits_licenses": "Salon sanitation certification renewal",
            "local_operating_restrictions": "Designated food zones, noise ordinances after 10 PM"
        },
        "section_09_capacity_and_constraints": {
            "monthly_customer_capacity": "400",
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
            "goals_12_month": "Increase net margins to 20% and expand high-ticket bridal service packages.",
            "goals_3_year": "Add a second location in West Loop and develop in-house organic product line.",
            "long_term_vision": "Premier organic beauty and holistic personal care brand in the Midwest.",
            "exit_strategy": "Pass on to key operator or sell brand to hospitality group in 8-10 years."
        },
        "section_12_pricing_and_revenue": {
            "pricing_method": [
                "Per unit",
                "Per job"
            ],
            "typical_order_size": "$145 styling ticket / $1,200 bridal package",
            "discounts_and_promotions": "10% discount on recurring corporate weekly bookings.",
            "customer_payment_methods": [
                "Upfront",
                "On delivery"
            ]
        },
        "section_13_hiring_and_team_structure": {
            "team_roles": "Creative Director, Senior Colorist, Stylists, Front Desk Manager, Apprentices",
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
                "Social media",
                "Online search",
                "Referrals"
            ],
            "delivery_methods": [
                "In-person",
                "Retail store"
            ],
            "tracks_leads_crm": "Spreadsheet",
            "lead_conversion_rate": "35%",
            "monthly_marketing_budget": "500"
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
            "active_opportunities": {"count": 5, "descriptor": "Browse salon matches"},
            "new_this_week": {"count": 1, "label": "1 new this week"},
            "total_potential_value": "$14,800",
            "avg_fit_score": 89,
            "event_readiness_index": 87,
            "historical_roi": {"multiplier": "2.8x", "sample_size": 3}
        },
        "recommended_hero": {
            "id": "opp_salon_hero",
            "type": "Venue Residency",
            "box_type": "Direct Match",
            "out_box": False,
            "title": "Chicago Logan Square Spring Wedding Fair & Bridal Package",
            "source": "Logan Square Merchants Association",
            "match_score": 92,
            "readiness_score": 88,
            "data_trust_indicator": "Verified",
            "risk_level": "Low",
            "drive_time_minutes": 8,
            "distance_miles": 0.8,
            "expires_at": "Closes in 12 days",
            "estimated_revenue": "$4,800/mo bridal packages",
            "listed_fee": "$150 vendor table",
            "why_reason_codes": ["Leverages high-margin bridal party styling demand"],
            "risk_signals": ["Requires Saturday morning staffing commitments"],
            "verify_flag": False,
            "verify_flag_message": None,
            "registration_url": "https://logansquaremerchants.org/bridal-apply",
            "source_url": "https://logansquaremerchants.org/events"
        },
        "more_matches": [],
        "recommended": [
            {
                "id": "opp_salon_1",
                "title": "Bridal Package & Retail Cross-Sell Expansion",
                "impact": "+$4,800/mo bridal revenue",
                "strategic_fit": "High-margin weekend service expansion",
                "execution_steps": [
                    "Create bridal party package flyer with retail product gift box",
                    "Promote bridal styling packages on Instagram and Knot directory"
                ],
                "risk_rating": "Low"
            }
        ],
        "selected_tracked": [
            {
                "id": "track_salon_1",
                "title": "Logan Square Spring Wedding Fair",
                "type": "Venue Residency",
                "status": "Tracked",
                "estimated_revenue": "$4,800",
                "next_checkpoint": "Day 4 check-in in 2 days"
            }
        ],
        "portfolio_summary": {
            "active_count": 1,
            "past_count": 3,
            "total_committed_dollars": "$4,800"
        }
    },

    # 8. SCENARIOS PAYLOAD
    "scenarios": {
        "scenario_id": "scen_salon_bridal",
        "confidence": 89,
        "risk": "Low",
        "impact_cards": [
            {"label": "Bridal Sales Inflow", "value": "+$4,800", "direction": "up"},
            {"label": "Net Margin Lift", "value": "+2.1%", "direction": "up"},
            {"label": "Cash Buffer Increase", "value": "+1.2 Months", "direction": "up"}
        ]
    }
}
