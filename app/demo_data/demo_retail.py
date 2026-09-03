# backend/app/demo_data/demo_retail.py
"""
Complete spec-compliant demo payload for Business #2: Main St Goods (demo-retail).
Follows exact FA V6 schemas (DASHBOARD MODE, INSIGHTS MODE, DRAWER MODE), Demand Forecast (v9 Split), Business Health, 16-section Business Profile, Opportunities V2 (Research Scout V3.1), and Scenario Lab.
"""

MAIN_ST_GOODS_PAYLOADS = {
    "account": {
        "login_label": "demo-retail",
        "business_name": "Main St Goods",
        "email": "demo-retail@lightsignal.app",
        "industry": "Gift & Home Goods Retail",
        "owner": "Dana Whitfield",
        "is_demo": True,
    },
    
    # 1. DASHBOARD MODE PAYLOAD
    "dashboard": {
        "summary": "Main St Goods monthly revenue is $34,200 MTD. Pre-season $14K inventory PO dip tightened cash runway to 4.8 months.",
        "kpis": {
            "revenue_mtd": {"value": 34200.0, "prior_value": 32500.0, "format_type": "currency", "link": "/overview#revenue"},
            "net_margin_pct": {"value": 0.118, "prior_value": 0.142, "format_type": "percentage", "link": "/overview#margin"},
            "cash": {"value": 28400.0, "prior_value": 42400.0, "format_type": "currency", "link": "/overview#cash"},
            "runway_months": {"value": 4.8, "prior_value": 7.2, "format_type": "months", "link": "/overview#runway"},
            "ai_health_score": {"value": 78, "prior_value": 82, "format_type": "score", "link": "/overview#health"},
        },
        "alerts": [
            {
                "severity": "below_average",
                "type": "warning",
                "message": "Pre-holiday inventory PO of $14K reduced cash reserves to 4.8 months runway",
                "icon": "🟡"
            },
            {
                "severity": "critical",
                "type": "risk",
                "message": "Supplier tariff pass-through +9% compressing blended margin from 52% to 48%",
                "icon": "🔴"
            },
            {
                "severity": "above_average",
                "type": "positive",
                "message": "SBA loan repayment of $780/mo on track; WOSB status paths active",
                "icon": "🟢"
            }
        ],
        "insight_pairs": [
            {
                "head": "Pre-Season Inventory Cash Outflow",
                "problem": "$14,000 bulk inventory buy ahead of peak season reduced liquid cash buffer to $28,400 (4.8 months runway).",
                "solution": "Establish 30-day vendor payment terms on Q4 re-orders to preserve cash buffer through October."
            },
            {
                "head": "Import Category Tariff Margin Compression",
                "problem": "9% tariff cost increase on imported home decor line lowered overall retail gross margin from 52.0% to 48.0%.",
                "solution": "Apply selective +5% price adjustment on premium gift lines to offset supplier tariff pass-through."
            }
        ],
        "opportunities": [
            {
                "head": "Maker Pop-Up Events & Q4 Kiosk Expansion",
                "body": "Host local artisan pop-up markets to drive weekend foot traffic ahead of Asheville peak autumn tourist season."
            }
        ],
        "what_changed": [
            "Cash runway temporarily contracted from 7.2 to 4.8 months due to planned pre-holiday inventory buying.",
            "Gross margin adjusted to 48.0% following vendor tariff updates."
        ],
        "missing_data_notice": None
    },

    # 2. INSIGHTS MODE PAYLOAD
    "insights_mode": {
        "profitability_banner": {
            "status": "at_average",
            "headline": "Pre-season inventory buy complete; Q4 holiday revenue surge on track.",
            "supporting_text": "Gross margin at 48.0%, down 4.0 pts from tariff increases; cash dips expected before autumn rush.",
            "missing_data_notice": None
        },
        "items": [
            {
                "signal_id": "inventory_cash_dip",
                "pressing_score": 81,
                "tier": "tier_1",
                "headline": "Planned Inventory PO Dips Cash Buffer to $28.4K",
                "whats_going_on": "Chunky $14,000 PO outflow for Q4 stock reduced cash reserve. This is an expected pre-season inventory build ahead of Oct-Dec peak (which generates 38% of annual sales).",
                "why_it_matters_now": "Working capital must be managed closely through September until tourist foot traffic surges.",
                "what_to_do": "Stagger secondary inventory orders and negotiate NET-30 terms with local maker partners.",
                "expected_impact": {
                    "value_text": "+$18.5K net inventory value",
                    "calculation_basis": "Stocked inventory position unlocks $45K+ in Q4 retail sales at keystone markup."
                },
                "effort": "quick_win",
                "confidence": "high",
                "directive": {
                    "shape_id": "cash_runway_chart",
                    "state": "active",
                    "theme": "warning",
                    "numbers": {"cash_before": 42400.0, "po_outflow": -14000.0, "cash_after": 28400.0},
                    "labels": {"before": "Pre-PO Cash", "po": "Inventory Buy", "after": "Current Cash"}
                }
            }
        ],
        "missing_data_notice": None
    },

    # 3. DRAWER MODE PAYLOAD
    "drawer_mode": {
        "revenue": {
            "value_text": "$34,200",
            "status_badge": {"label": "Seasonal Track", "severity": "above_average"},
            "headline_read": "Monthly sales steady at $34.2K; preparing for October-December peak boost.",
            "benchmarks": {
                "peer_avg": "$31,000/mo",
                "sba_metric": "Above average for downtown Asheville retail",
                "position": "above",
                "gap_text": "10.3% ahead of regional retail benchmark"
            },
            "drivers": [
                {"description": "In-store Square POS purchases (94% share)", "impact": "+$32,148", "category": "Retail POS"},
                {"description": "Shopify buy-online-pick-up-in-store (6% share)", "impact": "+$2,052", "category": "E-commerce"}
            ],
            "actions": [
                {"description": "Schedule local artisan weekend pop-ups for late September", "priority": "high", "effort": "quick_win"}
            ]
        }
    },

    # 4. DEMAND FORECAST PAYLOAD
    "demand_forecast": {
        "metrics": {
            "forecast_series": [18700.0, 20400.0, 27200.0, 30600.0, 34000.0, 35700.0, 34000.0, 32300.0, 35700.0, 45900.0, 51000.0, 54400.0]
        },
        "flags": [
            {"severity": "amber", "title": "Pre-Season $14K PO Cash Dip"},
            {"severity": "red", "title": "Import Category Tariff Pass-Through (+9%)"}
        ],
        "data": {
            "historical_revenue": [
                {"date": "2026-01-01", "amount": 18700.0},
                {"date": "2026-02-01", "amount": 20400.0},
                {"date": "2026-03-01", "amount": 27200.0},
                {"date": "2026-04-01", "amount": 34200.0}
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
                        "headline": "Projected weekend retail sales of $5,400 across boutique footwear & apparel.",
                        "expected_value": "$5,400",
                        "expected_unit": "revenue",
                        "volume_forecast": 68,
                        "demand_unit": "Units",
                        "confidence_pct": 89,
                        "confidence_label": "High",
                        "anchor": "Anchored in Square POS 8-week weekend foot traffic & register transactions."
                    },
                    "swing_factor": {
                        "headline": "Downtown Art Walk (+22% foot traffic)",
                        "delta_text": "+$1,100",
                        "direction": "up",
                        "reasoning": "Friday evening sidewalk stroll boosting boutique storefront visits."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "Merchandise front window display & stock top 3 handbag SKUs", "severity": "above_average"},
                        "whats_moving": {"summary": "2 positive drivers (Art Walk, autumn outerwear pre-orders)", "severity": "above_average"},
                        "breakdown": {"summary": "58% footwear, 30% apparel, 12% accessories", "severity": "above_average"},
                        "track_record": {"summary": "Weekend forecast accuracy ran within 2.8% over last month", "severity": "above_average"},
                        "world_scan": {"summary": "Sunny 68°F forecast encouraging downtown shopping", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_retail_stock_01",
                            "action": "Restock front display with high-margin leather tote bags before Friday 4 PM",
                            "deadline": "Fri, Feb 7",
                            "priority": "high",
                            "tied_to_driver": "Downtown Art Walk",
                            "why_this_much": "Captures impulse tourist purchases during Art Walk hours.",
                            "dollar_logic": "Secures +$1,100 in high-margin accessory sales."
                        }
                    ],
                    "whats_moving": [
                        {
                            "name": "Downtown Art Walk",
                            "window": "This Weekend",
                            "severity": "green",
                            "impact_text": "+$1,100",
                            "reasoning": "Monthly gallery walk brings 2,500+ pedestrians to North Main St.",
                            "source": "Downtown Business Alliance",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 3800.0,
                        "expected_losses": 150.0,
                        "unbooked_demand": 1600.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Boutique weekend predictions hit within 2.8% of POS actuals.",
                        "lean_guidance": "Slight conservative bias on sunny event weekends."
                    },
                    "world_scan": [
                        {
                            "flag": "Asheville Downtown Art Walk",
                            "horizon": "Friday 5 PM - 9 PM",
                            "depends_on": "Storefront lighting & sidewalk display",
                            "action_yet": "Keep front doors open with warm welcome display",
                            "source": "City Tourism Board"
                        }
                    ]
                },
                {
                    "window": "Next 30 Days",
                    "severity": "amber",
                    "hero": {
                        "eyebrow": "Forward Demand Read",
                        "headline": "Pre-season inventory build complete; demand tracking at $34,200 ahead of autumn tourist peak.",
                        "expected_value": "$34,200",
                        "expected_unit": "revenue",
                        "confidence_pct": 85,
                        "confidence_label": "High",
                        "anchor": "Anchored in Square POS actuals + Asheville downtown tourism seasonality curves."
                    },
                    "swing_factor": {
                        "headline": "Pre-holiday inventory PO ($14,000 outflow)",
                        "delta_text": "-$14,000",
                        "direction": "down",
                        "reasoning": "Chunky stock pre-buy reduced liquid cash reserve to 4.8 months runway."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "2 actions to stagger Q4 supplier orders and offset tariff pass-through", "severity": "below_average"},
                        "whats_moving": {"summary": "3 key retail drivers (tourist walk-in, local makers, Shopify BOPIS)", "severity": "above_average"},
                        "breakdown": {"summary": "94% in-store Square POS, 6% Shopify pickup", "severity": "above_average"},
                        "track_record": {"summary": "Prior 90-day forecast ran within 4.1% of actual Square POS sales", "severity": "above_average"},
                        "world_scan": {"summary": "Asheville autumn foliage festival traffic tracking strong", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_mainst_1",
                            "title": "Establish 30-day vendor payment terms on Q4 re-orders",
                            "deadline": "Sep 01",
                            "priority": "high",
                            "tied_to_driver": "Pre-Season PO Cash Dip",
                            "why_this_much": "Preserves cash buffer through September ahead of peak tourist surge.",
                            "dollar_logic": "+$14,000 cash buffer protected"
                        },
                        {
                            "id": "act_mainst_2",
                            "title": "Apply 5% selective price adjustment on imported gift line",
                            "deadline": "Sep 15",
                            "priority": "medium",
                            "tied_to_driver": "Import Tariff Squeeze",
                            "why_this_much": "Offsets 9% supplier tariff increase to restore gross margin to 52%.",
                            "dollar_logic": "+$1,650/mo margin recovered"
                        }
                    ],
                    "drivers": [
                        {
                            "name": "Pre-Season PO Cash Dip",
                            "severity": "amber",
                            "window": "Next 30 Days",
                            "impact_text": "-$14,000",
                            "reasoning": "Chunky inventory buy before Q4 peak.",
                            "source": "QBO Purchase Orders",
                            "confidence": "high"
                        },
                        {
                            "name": "Import Tariff Squeeze",
                            "severity": "red",
                            "window": "Next 30 Days",
                            "impact_text": "-$1,650",
                            "reasoning": "9% tariff pass-through on home decor lines.",
                            "source": "Supplier Invoices",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 32148.0,
                        "expected_losses": 1650.0,
                        "unbooked_demand": 3702.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Prior 90-day forecast ran within 4.1% of actual Square POS sales.",
                        "lean_guidance": "Slight conservative bias on rainy Saturday foot traffic."
                    },
                    "world_scan": [
                        {
                            "flag": "Asheville Autumn Leaf Season Tourist Surge",
                            "horizon": "Oct-Nov",
                            "depends_on": "Downtown Asheville foot traffic count",
                            "action_yet": "Host local artisan weekend pop-up events in late September",
                            "source": "Asheville Chamber / Retail Scan"
                        }
                    ]
                }
            ]
        }
    },

    # 5. BUSINESS HEALTH PAYLOAD
    "business_health": {
        "overall_score": 78,
        "status": "Healthy",
        "dimensions": {
            "liquidity": {"score": 70, "label": "Moderate", "cash_months": 4.8},
            "profitability": {"score": 76, "label": "Good", "net_margin": 11.8},
            "growth": {"score": 85, "label": "High", "yoy_growth": 6.8},
            "efficiency": {"score": 80, "label": "Good", "inventory_turns": "4.2x"},
            "resilience": {"score": 79, "label": "Solid", "debt_load": "$780/mo SBA"}
        }
    },

    # 6. BUSINESS PROFILE PAYLOAD
    "business_profile": {
        "section_01_business_basics": {
            "business_name": "Main St Goods",
            "headquarters": "Asheville, NC",
            "years_in_business": "5 to 10 years",
            "timezone": "America/New_York",
            "currency": "USD",
            "legal_entity_type": "LLC",
            "ein": "56-1234567",
            "locations": [
                {
                    "name": "Main St Goods Boutique",
                    "address": "48 N Lexington Ave, Asheville, NC 28801",
                    "role": "Primary Retail Boutique",
                    "status": "active"
                }
            ]
        },
        "section_02_ownership_and_key_people": {
            "ownership_breakdown": "Dana Whitfield (100%)",
            "decision_maker": "Dana Whitfield, Founder & General Manager",
            "bookkeeper_financial_handler": "Blue Ridge Accounting (External)",
            "has_backup_operator": "Yes"
        },
        "section_03_industry_and_model": {
            "business_description": "Curated independent retail gift boutique showcasing handmade regional crafts, home decor, ceramics, and gifts.",
            "revenue_model_description": "Direct retail sales at boutique, buy-online-pickup-in-store, and pop-up events.",
            "target_market_type": "Both",
            "business_stage": "Growing and adding capacity"
        },
        "section_04_operations": {
            "team_size": "Small team of 4 to 10",
            "payroll_type": "Mostly employees with some contractors",
            "operating_hours": "Mon-Sat 10am-7pm, Sun 11am-5pm",
            "growth_limiters": [
                "Staff",
                "Equipment",
                "Time"
            ],
            "single_supplier_dependency": "We have key suppliers but alternatives exist",
            "uses_pos_system": "Yes",
            "space_ownership_status": "Lease it",
            "operational_software": [
                "E-commerce platform",
                "Inventory management",
                "Payroll software"
            ],
            "recent_supplier_issues": "No",
            "critical_materials_inputs": "Handmade pottery, local scented candles, bespoke stationery, custom gift wrapping."
        },
        "section_05_financial_overview": {
            "accounting_system": "QuickBooks",
            "connect_accounting_now": "Yes",
            "fiscal_year_start": "January to December (all 12 months)",
            "banks_and_lenders": "First Local Bank",
            "business_loan_history": "Yes and currently paying it"
        },
        "section_06_assets_and_equipment": {
            "major_assets": "Custom Wood Display Fixtures, Square Register Terminals, Inventory Storage Racks",
            "asset_ownership_status": "Truck is leased, internal equipment is owned",
            "asset_purchase_dates": "Store fixtures custom installed 2018, POS upgraded 2021",
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
            "typical_customers_description": "Tourists exploring downtown Asheville, regional weekend travelers, and loyal local residents buying artisan gifts.",
            "monthly_customer_volume": "805",
            "repeat_business_rate": "High",
            "target_customer_types": "Corporate offices looking for weekly lunch catering.",
            "customer_concentration": "No, spread across many",
            "seasonality_level": "A little seasonal",
            "customer_geographic_source": "Within 10–15 miles",
            "opportunity_radius_miles": "25",
            "max_travel_distance_miles": "75",
            "local_opportunity_preference": "Open to nearby areas if high-value",
            "geographic_service_areas": "Asheville Downtown, Buncombe County, and Regional North Carolina",
            "weather_impact": "High"
        },
        "section_08_risk_and_exposure": {
            "carries_business_insurance": "Yes",
            "critical_dependencies": "Downtown tourist foot traffic and key local artisan vendor consignments",
            "revenue_concentration": "No, spread across many",
            "active_permits_licenses": "City of Asheville Business License, NC Retail Sales Tax Registration",
            "in_progress_permits_licenses": "A-Frame Sidewalk Sign Permit",
            "local_operating_restrictions": "Designated food zones, noise ordinances after 10 PM"
        },
        "section_09_capacity_and_constraints": {
            "monthly_customer_capacity": "1200",
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
            "goals_12_month": "Increase net margins to 20% and launch curated corporate gift boxes.",
            "goals_3_year": "Add a second boutique location in Black Mountain and expand e-commerce sales.",
            "long_term_vision": "Build a recognized regional boutique retail & handmade maker hub.",
            "exit_strategy": "Pass on to key operator or sell brand to hospitality group in 8-10 years."
        },
        "section_12_pricing_and_revenue": {
            "pricing_method": [
                "Per unit",
                "Per job"
            ],
            "typical_order_size": "$42.50 retail ticket / $120 gift box",
            "discounts_and_promotions": "10% discount on recurring corporate weekly bookings.",
            "customer_payment_methods": [
                "Upfront",
                "On delivery"
            ]
        },
        "section_13_hiring_and_team_structure": {
            "team_roles": "Store Manager, Retail Sales Associate, Inventory Specialist",
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
                "Events",
                "Online search"
            ],
            "delivery_methods": [
                "In-person",
                "Online",
                "Retail store",
                "Delivery"
            ],
            "tracks_leads_crm": "Spreadsheet",
            "lead_conversion_rate": "35%",
            "monthly_marketing_budget": "450"
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
            "active_opportunities": {"count": 6, "descriptor": "Browse retail matches"},
            "new_this_week": {"count": 1, "label": "1 new this week"},
            "total_potential_value": "$16,500",
            "avg_fit_score": 86,
            "event_readiness_index": 82,
            "historical_roi": {"multiplier": "2.1x", "sample_size": 3}
        },
        "recommended_hero": {
            "id": "opp_retail_hero",
            "type": "Vendor Program",
            "box_type": "Direct Match",
            "out_box": False,
            "title": "Asheville Autumn Leaf Festival Retail Pop-Up",
            "source": "Asheville Downtown Association",
            "match_score": 90,
            "readiness_score": 86,
            "data_trust_indicator": "Verified",
            "risk_level": "Low",
            "drive_time_minutes": 5,
            "distance_miles": 0.4,
            "expires_at": "Closes in 10 days",
            "estimated_revenue": "$8,500 weekend",
            "listed_fee": "$250 booth fee",
            "why_reason_codes": ["Capitalizes on regional autumn leaf tourism peak"],
            "risk_signals": ["Weather dependent outdoor setup"],
            "verify_flag": False,
            "verify_flag_message": None,
            "registration_url": "https://ashevilledowntown.org/autumn-popup",
            "source_url": "https://ashevilledowntown.org/events"
        },
        "more_matches": [],
        "recommended": [
            {
                "id": "opp_retail_1",
                "title": "Asheville Autumn Tourist Pop-Up Market Series",
                "impact": "+$8,500/mo peak revenue",
                "strategic_fit": "Capitalizes on regional autumn leaf tourism peak",
                "execution_steps": [
                    "Host weekend artisan pop-ups in front of Main St storefront",
                    "Promote pop-up schedule via local hotel concierge networks"
                ],
                "risk_rating": "Low"
            }
        ],
        "selected_tracked": [
            {
                "id": "track_retail_1",
                "title": "Asheville Autumn Tourist Pop-Up Market Series",
                "type": "Vendor Program",
                "status": "Tracked",
                "estimated_revenue": "$8,500",
                "next_checkpoint": "Day 5 check-in in 3 days"
            }
        ],
        "portfolio_summary": {
            "active_count": 1,
            "past_count": 3,
            "total_committed_dollars": "$8,500"
        }
    },

    # 8. SCENARIOS PAYLOAD
    "scenarios": {
        "scenario_id": "scen_retail_popup",
        "confidence": 85,
        "risk": "Low",
        "impact_cards": [
            {"label": "Q4 Sales Surge", "value": "+$8,500", "direction": "up"},
            {"label": "Net Margin Recovery", "value": "+2.4%", "direction": "up"},
            {"label": "Cash Buffer Rebound", "value": "+2.4 Months", "direction": "up"}
        ]
    }
}
