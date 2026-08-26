# backend/app/demo_data/demo_multi.py
"""
Complete spec-compliant demo payload for Business #5: Driftwood Coffee Roasters (demo-multi).
Follows exact FA V6 schemas (DASHBOARD MODE, INSIGHTS MODE, DRAWER MODE), Demand Forecast (v9 Split), Business Health, 16-section Business Profile, Opportunities V2 (Research Scout V3.1), and Scenario Lab.
"""

DRIFTWOOD_COFFEE_PAYLOADS = {
    "account": {
        "login_label": "demo-multi",
        "business_name": "Driftwood Coffee Roasters",
        "email": "demo-multi@lightsignal.app",
        "industry": "Multi-location Cafe & Roastery",
        "owner": "Sam Okafor",
        "is_demo": True,
    },
    
    # 1. DASHBOARD MODE PAYLOAD
    "dashboard": {
        "summary": "Driftwood Coffee revenue reached $76,500 MTD. Per-location divergence: Alberta flagship is profitable (+58% share), while Division satellite runs at -$1,800/mo deficit.",
        "kpis": {
            "revenue_mtd": {"value": 76500.0, "prior_value": 74200.0, "format_type": "currency", "link": "/overview#revenue"},
            "net_margin_pct": {"value": 0.124, "prior_value": 0.148, "format_type": "percentage", "link": "/overview#margin"},
            "cash": {"value": 52000.0, "prior_value": 54500.0, "format_type": "currency", "link": "/overview#cash"},
            "runway_months": {"value": 9.2, "prior_value": 10.1, "format_type": "months", "link": "/overview#runway"},
            "ai_health_score": {"value": 79, "prior_value": 83, "format_type": "score", "link": "/overview#health"},
        },
        "alerts": [
            {
                "severity": "critical",
                "type": "risk",
                "message": "Division St satellite operating at -$1,800/mo net loss vs allocated overhead",
                "icon": "🔴"
            },
            {
                "severity": "below_average",
                "type": "warning",
                "message": "Green coffee bean market spike +18% compressing wholesale gross margin to 38%",
                "icon": "🟡"
            },
            {
                "severity": "above_average",
                "type": "positive",
                "message": "Coffee subscription pilot generated $2,900/mo in new recurring revenue",
                "icon": "🟢"
            }
        ],
        "insight_pairs": [
            {
                "head": "Per-Location Performance Divergence",
                "problem": "Alberta flagship generates 58% of cafe sales ($26.1K) with healthy operating profit, while Division satellite generates 42% ($18.9K) and runs at -$1,800/mo deficit.",
                "solution": "Adjust Division staff scheduling during slow 2-5 PM hours and push local wholesale accounts to share roasting overhead."
            },
            {
                "head": "Green Coffee Wholesale Margin Squeeze",
                "problem": "Green coffee import costs rose +18%, compressing wholesale roasting margin from 44.0% to 38.0% across 14 wholesale restaurant accounts.",
                "solution": "Introduce a 45-cent/lb price adjustment on wholesale contracts and leverage roaster capacity headroom (currently 60% utilized)."
            }
        ],
        "opportunities": [
            {
                "head": "Roastery Headroom & Subscription Growth",
                "body": "12kg roaster is running at only 60% capacity; expanding DTC coffee subscriptions can add high-margin volume without capital expenditure."
            }
        ],
        "what_changed": [
            "Division St satellite progress stalled at -$1,800/mo loss while Alberta flagship grew 5.2%.",
            "Coffee subscription pilot added $2,900/mo in predictable recurring revenue."
        ],
        "missing_data_notice": None
    },

    # 2. INSIGHTS MODE PAYLOAD
    "insights_mode": {
        "profitability_banner": {
            "status": "at_average",
            "headline": "Alberta flagship strong; Division location breakeven is primary operational focus.",
            "supporting_text": "Cafe retail gross margin at 68.0%; wholesale margin compressed to 38.0% by green coffee input costs.",
            "missing_data_notice": None
        },
        "items": [
            {
                "signal_id": "location_divergence",
                "pressing_score": 86,
                "tier": "tier_1",
                "headline": "Division St Satellite Running at -$1.8K/mo Operating Deficit",
                "whats_going_on": "Square POS multi-location breakdown reveals Alberta Arts flagship generates $26.1K/mo at a 22% net profit margin, while Division St generates $18.9K/mo and loses $1,800/mo after labor and lease allocation.",
                "why_it_matters_now": "The Division deficit offsets 32% of the flagship's operating profit, capping business-wide net cash generation.",
                "what_to_do": "Cross-train Division baristas for roastery prep, re-negotiate weekday afternoon labor shifts, and launch targeted Richmond neighborhood sampling.",
                "expected_impact": {
                    "value_text": "+$1,800/mo profit recovered",
                    "calculation_basis": "Bringing Division St to breakeven increases total business net income from $9.5K to $11.3K monthly."
                },
                "effort": "moderate",
                "confidence": "high",
                "directive": {
                    "shape_id": "location_comparison_bar",
                    "state": "active",
                    "theme": "critical",
                    "numbers": {"alberta_rev": 26100.0, "alberta_profit": 5742.0, "division_rev": 18900.0, "division_profit": -1800.0},
                    "labels": {"alberta": "Alberta (Flagship)", "division": "Division (Satellite)"}
                }
            }
        ],
        "missing_data_notice": None
    },

    # 3. DRAWER MODE PAYLOAD
    "drawer_mode": {
        "revenue": {
            "value_text": "$76,500",
            "status_badge": {"label": "Dual-Stream Growth", "severity": "above_average"},
            "headline_read": "Revenue steady at $76.5K MTD; 59% cafe sales, 37% wholesale accounts, 4% subscriptions.",
            "benchmarks": {
                "peer_avg": "$68,000/mo",
                "sba_metric": "Above average for Portland multi-location roasters",
                "position": "above",
                "gap_text": "12.5% above regional roaster benchmark"
            },
            "drivers": [
                {"description": "Alberta & Division cafe retail (59% share)", "impact": "+$45,000", "category": "Cafe Sales"},
                {"description": "Wholesale roastery accounts (37% share)", "impact": "+$28,600", "category": "Wholesale"},
                {"description": "DTC coffee subscriptions (4% share)", "impact": "+$2,900", "category": "Subscriptions"}
            ],
            "actions": [
                {"description": "Implement afternoon labor reduction at Division satellite location", "priority": "high", "effort": "quick_win"},
                {"description": "Apply 45-cent/lb price adjustment to wholesale green coffee contracts", "priority": "medium", "effort": "moderate"}
            ]
        }
    },

    # 4. DEMAND FORECAST PAYLOAD
    "demand_forecast": {
        "metrics": {
            "forecast_series": [72675.0, 72675.0, 76500.0, 76500.0, 76500.0, 70380.0, 67320.0, 68850.0, 76500.0, 80325.0, 84150.0, 91800.0]
        },
        "flags": [
            {"severity": "red", "title": "Division St Satellite Deficit (-$1.8K/mo)"},
            {"severity": "amber", "title": "Green Coffee Input Cost Spike (+18%)"}
        ],
        "data": {
            "historical_revenue": [
                {"date": "2026-01-01", "amount": 72675.0},
                {"date": "2026-02-01", "amount": 72675.0},
                {"date": "2026-03-01", "amount": 76500.0},
                {"date": "2026-04-01", "amount": 76500.0}
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
                        "headline": "Projected multi-location weekend revenue of $12,400 across Flagship & Satellite cafes.",
                        "expected_value": "$12,400",
                        "expected_unit": "revenue",
                        "volume_forecast": 1650,
                        "demand_unit": "Transactions",
                        "confidence_pct": 91,
                        "confidence_label": "High",
                        "anchor": "Anchored in Square POS 12-week multi-location weekend ticket averages."
                    },
                    "swing_factor": {
                        "headline": "Downtown Farmers Market (+15% Flagship foot traffic)",
                        "delta_text": "+$1,850",
                        "direction": "up",
                        "reasoning": "High weekend pedestrian traffic boosting espresso & cold brew beverage sales."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "Shift 1 barista to Flagship & stock 20 gal oat milk", "severity": "above_average"},
                        "whats_moving": {"summary": "2 key demand drivers (Farmers Market, weekend pastry popup)", "severity": "above_average"},
                        "breakdown": {"summary": "68% Flagship Location, 32% Satellite Location", "severity": "above_average"},
                        "track_record": {"summary": "Multi-unit weekend forecast accuracy ran within 2.2% over past month", "severity": "above_average"},
                        "world_scan": {"summary": "Sunny 74°F weather expected across both location districts", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_multi_shift_01",
                            "action": "Reassign 1 barista from Division St to Flagship Saturday morning shift",
                            "deadline": "Fri, Feb 7",
                            "priority": "high",
                            "tied_to_driver": "Downtown Farmers Market",
                            "why_this_much": "Prevents queue bottlenecks during 9 AM - 12 PM peak.",
                            "dollar_logic": "Secures +$1,850 in high-margin espresso beverage volume."
                        }
                    ],
                    "whats_moving": [
                        {
                            "name": "Downtown Farmers Market",
                            "window": "This Weekend",
                            "severity": "green",
                            "impact_text": "+$1,850",
                            "reasoning": "Weekly weekend market draws 3,000+ shoppers to Flagship block.",
                            "source": "City Farmers Market Alliance",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 8200.0,
                        "expected_losses": 300.0,
                        "unbooked_demand": 4500.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Multi-location weekend predictions hit within 2.2% of POS actuals.",
                        "lean_guidance": "High precision across both store locations."
                    },
                    "world_scan": [
                        {
                            "flag": "Flagship Block Sidewalk Maintenance",
                            "horizon": "Sunday 6 AM - 11 AM",
                            "depends_on": "Side entrance accessibility",
                            "action_yet": "Put up side door directional signage",
                            "source": "Municipal Works Notice"
                        }
                    ]
                },
                {
                    "window": "Next 30 Days",
                    "severity": "amber",
                    "hero": {
                        "eyebrow": "Forward Demand Read",
                        "headline": "Multi-location revenue tracking at $76,500 MTD; Division location breakeven is key focus.",
                        "expected_value": "$76,500",
                        "expected_unit": "revenue",
                        "confidence_pct": 86,
                        "confidence_label": "High",
                        "anchor": "Anchored in Square multi-location POS data + 14 recurring wholesale roastery accounts."
                    },
                    "swing_factor": {
                        "headline": "Division St satellite operating deficit (-$1,800/mo)",
                        "delta_text": "-$1,800",
                        "direction": "down",
                        "reasoning": "Division location revenue lagging allocated labor & lease cost."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "2 actions to optimize Division afternoon labor and adjust wholesale lb rates", "severity": "below_average"},
                        "whats_moving": {"summary": "3 revenue drivers (Alberta flagship, Division satellite, wholesale accounts)", "severity": "above_average"},
                        "breakdown": {"summary": "59% cafe retail, 37% wholesale roastery, 4% subscriptions", "severity": "above_average"},
                        "track_record": {"summary": "Prior 90-day forecast ran within 3.9% of Square POS actuals", "severity": "above_average"},
                        "world_scan": {"summary": "Portland Alberta Arts & Division neighborhood coffee foot traffic steady", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_multi_1",
                            "title": "Adjust Division St afternoon barista staffing schedule (2-5 PM window)",
                            "deadline": "Feb 12",
                            "priority": "high",
                            "tied_to_driver": "Division Location Deficit",
                            "why_this_much": "Eliminates $1,800/mo deficit to bring satellite location to breakeven.",
                            "dollar_logic": "+$1,800/mo profit recovered"
                        },
                        {
                            "id": "act_multi_2",
                            "title": "Apply 45-cent/lb price adjustment on 14 wholesale roastery accounts",
                            "deadline": "Mar 01",
                            "priority": "medium",
                            "tied_to_driver": "Green Coffee Inflation",
                            "why_this_much": "Restores wholesale roasting margin to 44% baseline.",
                            "dollar_logic": "+$1,280/mo wholesale margin recovered"
                        }
                    ],
                    "drivers": [
                        {
                            "name": "Division Location Deficit",
                            "severity": "red",
                            "window": "Next 30 Days",
                            "impact_text": "-$1,800",
                            "reasoning": "Division St operating sales lagging allocated overhead.",
                            "source": "Square POS Multi-Location",
                            "confidence": "high"
                        },
                        {
                            "name": "Green Coffee Inflation",
                            "severity": "amber",
                            "window": "Next 30 Days",
                            "impact_text": "-$1,280",
                            "reasoning": "Green bean import market cost up 18%.",
                            "source": "Roastery Invoices",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 45000.0,
                        "expected_losses": 1800.0,
                        "unbooked_demand": 33300.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Prior 90-day forecast ran within 3.9% of actual Square POS sales.",
                        "lean_guidance": "Slight conservative bias on rainy weekday cafe foot traffic."
                    },
                    "world_scan": [
                        {
                            "flag": "Portland Specialty Coffee Roast Headroom",
                            "horizon": "Feb-Apr",
                            "depends_on": "Roastery 12kg equipment utilization (currently 60%)",
                            "action_yet": "Expand DTC coffee subscription marketing",
                            "source": "Roastery Ops Log"
                        }
                    ]
                }
            ]
        }
    },

    # 5. BUSINESS HEALTH PAYLOAD
    "business_health": {
        "overall_score": 79,
        "status": "Healthy",
        "dimensions": {
            "liquidity": {"score": 80, "label": "Good", "cash_months": 9.2},
            "profitability": {"score": 74, "label": "Moderate", "net_margin": 12.4},
            "growth": {"score": 83, "label": "Steady", "yoy_growth": 5.8},
            "efficiency": {"score": 72, "label": "Needs Action", "location_variance": "Division Deficit"},
            "resilience": {"score": 86, "label": "High", "debt_load": "$1,150/mo Equipment"}
        }
    },

    # 6. BUSINESS PROFILE PAYLOAD
    "business_profile": {
        "section_1_basics": {
            "business_name": "Driftwood Coffee Roasters",
            "legal_entity": "Driftwood Coffee Group LLC",
            "year_founded": 2016,
            "headquarters": "Portland, OR (Alberta Arts District)",
            "website": "https://driftwoodcoffeeroasters.com",
            "operating_mode": "Multi-location Specialty Cafe & Wholesale Roastery"
        },
        "section_2_ownership": {
            "owner_name": "Sam Okafor",
            "ownership_pct": 100.0,
            "role": "Founder & Head Roaster",
            "years_in_business": 10
        },
        "section_3_industry": {
            "primary_industry": "Commercial Roasting & Retail Coffee Shops",
            "naics_code": "311920",
            "niche": "Direct-Trade Specialty Coffee & Multi-Cafe Retail"
        },
        "section_4_operations": {
            "days_open_per_week": 7,
            "operating_hours": "7:00 AM - 5:00 PM (Daily)",
            "pos_system": "Square POS (Multi-Location Sync)",
            "roasting_equipment": "1x Diedrich IR-12 Industrial Roaster"
        },
        "section_5_financial": {
            "annual_revenue": 918000.0,
            "gross_margin_pct": 68.0,
            "net_margin_pct": 12.4,
            "monthly_cash_flow": 9485.0,
            "accounting_software": "QuickBooks Online"
        },
        "section_6_assets": {
            "real_estate": "Leased Alberta Flagship & Division Satellite",
            "equipment_value": 115000.0,
            "inventory_valuation": 28000.0
        },
        "section_7_customers": {
            "customer_type": "B2C Cafe Guests & B2B Wholesale Accounts",
            "average_ticket": 8.75,
            "monthly_transacting_customers": 5140
        },
        "section_8_risk": {
            "top_cost_exposure": "Green Coffee Market Inflation (+18%)",
            "capacity_risk": "Division Satellite Operating Deficit (-$1.8K/mo)"
        },
        "section_9_capacity": {
            "roaster_capacity_kg_per_week": 500,
            "current_roaster_utilization": 60.0,
            "locations_count": 2
        },
        "section_10_opportunity_readiness": {
            "roaster_headroom": "40% available capacity for wholesale/DTC expansion",
            "dtc_subscriptions": "Active (4% revenue share)"
        },
        "section_11_goals": {
            "target_annual_revenue": 1100000.0,
            "margin_target": 16.0,
            "growth_focus": "DTC coffee subscriptions & Division location breakeven"
        },
        "section_12_pricing": {
            "pricing_tier": "Specialty Premium",
            "price_points": {"12oz_whole_bean": "$21", "espresso_drink": "$5.75", "wholesale_lb": "$11.50"}
        },
        "section_13_team": {
            "full_time_staff": 6,
            "part_time_staff": 8,
            "key_personnel": "Head Roaster, Alberta Store Manager, Division Lead Barista"
        },
        "section_14_marketing": {
            "primary_channels": "Instagram, Wholesale Tastings, Subscription Email Sequences",
            "monthly_ad_budget": 800.0
        },
        "section_15_owner_prefs": {
            "risk_tolerance": "Moderate",
            "funding_preference": "Reinvest cafe profits & equipment lease ($1,150/mo)"
        },
        "section_16_docs": {
            "connected_systems": ["Square Multi-Location", "QuickBooks Online", "Shopify Subscriptions"],
            "verification_status": "Verified"
        }
    },

    # 7. OPPORTUNITIES V2 PAYLOAD
    "opportunities": {
        "kpis": {
            "active_opportunities": {"count": 8, "descriptor": "Browse roastery matches"},
            "new_this_week": {"count": 2, "label": "2 new this week"},
            "total_potential_value": "$22,400",
            "avg_fit_score": 90,
            "event_readiness_index": 86,
            "historical_roi": {"multiplier": "2.6x", "sample_size": 4}
        },
        "recommended_hero": {
            "id": "opp_multi_hero",
            "type": "Vendor Program",
            "box_type": "Direct Match",
            "out_box": False,
            "title": "Portland Specialty Coffee Guild Wholesale Exchange",
            "source": "Portland Coffee Association",
            "match_score": 93,
            "readiness_score": 88,
            "data_trust_indicator": "Verified",
            "risk_level": "Low",
            "drive_time_minutes": 10,
            "distance_miles": 2.0,
            "expires_at": "Closes in 15 days",
            "estimated_revenue": "$12,800/mo wholesale",
            "listed_fee": "$200 annual membership",
            "why_reason_codes": ["Utilizes 40% unused 12kg roaster capacity headroom"],
            "risk_signals": ["Requires green bean inventory buffer"],
            "verify_flag": False,
            "verify_flag_message": None,
            "registration_url": "https://portlandcoffee.org/wholesale-join",
            "source_url": "https://portlandcoffee.org/listings"
        },
        "more_matches": [],
        "recommended": [
            {
                "id": "opp_multi_1",
                "title": "DTC Coffee Subscription Expansion",
                "impact": "+$2,900/mo recurring revenue",
                "strategic_fit": "High-margin roaster capacity utilization",
                "execution_steps": [
                    "Add subscription purchase option on Shopify storefront",
                    "Offer 15% discount on 3-month recurring bean subscriptions"
                ],
                "risk_rating": "Low"
            }
        ],
        "selected_tracked": [
            {
                "id": "track_multi_1",
                "title": "DTC Coffee Subscription Expansion",
                "type": "Vendor Program",
                "status": "Tracked",
                "estimated_revenue": "$2,900/mo",
                "next_checkpoint": "Day 4 check-in in 2 days"
            }
        ],
        "portfolio_summary": {
            "active_count": 1,
            "past_count": 4,
            "total_committed_dollars": "$12,800"
        }
    },

    # 8. SCENARIOS PAYLOAD
    "scenarios": {
        "scenario_id": "scen_multi_sub",
        "confidence": 90,
        "risk": "Low",
        "impact_cards": [
            {"label": "Subscribers Recurring Cash", "value": "+$2,900", "direction": "up"},
            {"label": "Wholesale Margin Boost", "value": "+1.9%", "direction": "up"},
            {"label": "Roaster Capacity Utilization", "value": "+15%", "direction": "up"}
        ]
    }
}
