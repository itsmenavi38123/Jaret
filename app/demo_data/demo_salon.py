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
        "section_1_basics": {
            "business_name": "Velvet & Vine Salon",
            "legal_entity": "Raman Beauty Concepts LLC",
            "year_founded": 2019,
            "headquarters": "Chicago, IL (Logan Square)",
            "website": "https://velvetandvinesalon.com",
            "operating_mode": "Boutique Hair Salon & Personal Care"
        },
        "section_2_ownership": {
            "owner_name": "Priya Raman",
            "ownership_pct": 100.0,
            "role": "Founder & Creative Director",
            "years_in_business": 7
        },
        "section_3_industry": {
            "primary_industry": "Hair, Nail, & Skin Care Services",
            "naics_code": "812112",
            "niche": "Specialty Color & Organic Hair Treatment"
        },
        "section_4_operations": {
            "days_open_per_week": 5,
            "operating_hours": "10:00 AM - 8:00 PM (Tue-Sat)",
            "pos_system": "Square Appointments",
            "salon_chairs": 8
        },
        "section_5_financial": {
            "annual_revenue": 486000.0,
            "gross_margin_pct": 55.0,
            "net_margin_pct": 16.2,
            "monthly_cash_flow": 6560.0,
            "accounting_software": "QuickBooks Online"
        },
        "section_6_assets": {
            "real_estate": "Leased salon space (1,600 sq ft)",
            "equipment_value": 45000.0,
            "inventory_valuation": 12500.0
        },
        "section_7_customers": {
            "customer_type": "B2C Repeat Neighborhood Clients",
            "average_ticket": 145.0,
            "monthly_transacting_customers": 280
        },
        "section_8_risk": {
            "top_cost_exposure": "Unconfirmed No-Show Cancellation Rate (11%)",
            "capacity_risk": "Key-person senior colorist leave"
        },
        "section_9_capacity": {
            "salon_chairs": 8,
            "weekly_available_hours": 320,
            "current_chair_utilization": 68.0
        },
        "section_10_opportunity_readiness": {
            "bridal_services": "Active (High spring wedding demand)",
            "retail_product_attach": "13% (Target 15%)"
        },
        "section_11_goals": {
            "target_annual_revenue": 550000.0,
            "margin_target": 18.0,
            "growth_focus": "Bridal package marketing & retail attach expansion"
        },
        "section_12_pricing": {
            "pricing_tier": "Boutique Premium",
            "price_points": {"balayage_color": "$240", "haircut_style": "$85", "treatment": "$65"}
        },
        "section_13_team": {
            "full_time_staff": 4,
            "part_time_staff": 3,
            "key_personnel": "Creative Director, Senior Colorist, Front Desk Manager"
        },
        "section_14_marketing": {
            "primary_channels": "Instagram, Square Loyalty SMS, Local Wedding Blogs",
            "monthly_ad_budget": 500.0
        },
        "section_15_owner_prefs": {
            "risk_tolerance": "Conservative",
            "funding_preference": "Reinvest profits, zero debt"
        },
        "section_16_docs": {
            "connected_systems": ["Square Appointments", "QuickBooks Online"],
            "verification_status": "Verified"
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
