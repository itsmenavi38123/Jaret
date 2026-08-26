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
        "section_1_basics": {
            "business_name": "Main St Goods",
            "legal_entity": "Whitfield Goods & Gifts LLC",
            "year_founded": 2018,
            "headquarters": "Asheville, NC",
            "website": "https://mainstgoods.com",
            "operating_mode": "Boutique Retail Store & Online BOPIS"
        },
        "section_2_ownership": {
            "owner_name": "Dana Whitfield",
            "ownership_pct": 100.0,
            "role": "Founder & General Manager",
            "years_in_business": 8
        },
        "section_3_industry": {
            "primary_industry": "Retail - Gift, Novelty, & Souvenir Shops",
            "naics_code": "453220",
            "niche": "Curated Local Artisan & Home Decor"
        },
        "section_4_operations": {
            "days_open_per_week": 7,
            "operating_hours": "10:00 AM - 7:00 PM (Mon-Sat), 11:00 AM - 5:00 PM (Sun)",
            "pos_system": "Square Register",
            "ecommerce_platform": "Shopify POS Sync"
        },
        "section_5_financial": {
            "annual_revenue": 410000.0,
            "gross_margin_pct": 48.0,
            "net_margin_pct": 11.8,
            "monthly_cash_flow": 4035.0,
            "accounting_software": "QuickBooks Online"
        },
        "section_6_assets": {
            "real_estate": "Leased storefront on Main Street (1,200 sq ft)",
            "equipment_value": 24000.0,
            "inventory_valuation": 68000.0
        },
        "section_7_customers": {
            "customer_type": "B2C Tourists & Local Downtown Shoppers",
            "average_ticket": 42.50,
            "monthly_transacting_customers": 805
        },
        "section_8_risk": {
            "top_cost_exposure": "Import Tariff Pass-Through on Home Decor (+9%)",
            "capacity_risk": "Pre-season cash buffer squeeze ahead of Q4 tourist surge"
        },
        "section_9_capacity": {
            "storefront_square_footage": 1200,
            "max_daily_customer_capacity": 250,
            "current_capacity_utilization": 65.0
        },
        "section_10_opportunity_readiness": {
            "bopis_integration": "Active (Shopify + Square)",
            "artisan_partner_network": "34 local North Carolina makers"
        },
        "section_11_goals": {
            "target_annual_revenue": 480000.0,
            "margin_target": 15.0,
            "growth_focus": "Q4 local maker pop-up market expansion"
        },
        "section_12_pricing": {
            "pricing_tier": "Mid-Range",
            "price_points": {"artisan_candle": "$28", "ceramic_vase": "$45", "greeting_card": "$6"}
        },
        "section_13_team": {
            "full_time_staff": 2,
            "part_time_staff": 3,
            "key_personnel": "Store Manager, Inventory Specialist"
        },
        "section_14_marketing": {
            "primary_channels": "Downtown Merchant Association, Instagram, Local Tourist Guides",
            "monthly_ad_budget": 450.0
        },
        "section_15_owner_prefs": {
            "risk_tolerance": "Moderate",
            "funding_preference": "SBA Microloan ($780/mo existing) & operational cash"
        },
        "section_16_docs": {
            "connected_systems": ["Square POS", "Shopify", "QuickBooks Online"],
            "verification_status": "Verified"
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
