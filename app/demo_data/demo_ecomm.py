# backend/app/demo_data/demo_ecomm.py
"""
Complete spec-compliant demo payload for Business #6: Lakeshore Candle Co. (demo-ecomm).
Follows exact FA V6 schemas (DASHBOARD MODE, INSIGHTS MODE, DRAWER MODE), Demand Forecast (v9 Split), Business Health, 16-section Business Profile, Opportunities V2 (Research Scout V3.1), and Scenario Lab.
"""

LAKESHORE_CANDLE_PAYLOADS = {
    "account": {
        "login_label": "demo-ecomm",
        "business_name": "Lakeshore Candle Co.",
        "email": "demo-ecomm@lightsignal.app",
        "industry": "DTC E-Commerce & Home Fragrance",
        "owner": "Erin Kowalski",
        "is_demo": True,
    },
    
    # 1. DASHBOARD MODE PAYLOAD
    "dashboard": {
        "summary": "Lakeshore Candle Co. DTC sales reached $29,000 MTD. Meta ad ROAS fatigue (3.4 -> 2.4) compressed net contribution margin to 28.5%.",
        "kpis": {
            "revenue_mtd": {"value": 29000.0, "prior_value": 31200.0, "format_type": "currency", "link": "/overview#revenue"},
            "net_margin_pct": {"value": 0.142, "prior_value": 0.185, "format_type": "percentage", "link": "/overview#margin"},
            "cash": {"value": 38500.0, "prior_value": 44100.0, "format_type": "currency", "link": "/overview#cash"},
            "runway_months": {"value": 7.2, "prior_value": 8.5, "format_type": "months", "link": "/overview#runway"},
            "ai_health_score": {"value": 77, "prior_value": 81, "format_type": "score", "link": "/overview#health"},
        },
        "alerts": [
            {
                "severity": "critical",
                "type": "risk",
                "message": "Meta ad ROAS declined from 3.4 to 2.4, squeezing contribution margin",
                "icon": "🔴"
            },
            {
                "severity": "below_average",
                "type": "warning",
                "message": "USPS postal rate increase +6% added $380/mo to fulfillment costs",
                "icon": "🟡"
            },
            {
                "severity": "above_average",
                "type": "positive",
                "message": "Klaviyo VIP email campaign generated 3.4x revenue spike ($4,800 day)",
                "icon": "🟢"
            }
        ],
        "insight_pairs": [
            {
                "head": "Meta Ad ROAS Fatigue Squeeze",
                "problem": "Meta customer acquisition cost (CAC) increased as ROAS slid from 3.4 to 2.4 on $4,200/mo ad spend, reducing contribution margin by 9.5 percentage points.",
                "solution": "Refresh Meta ad creative, re-allocate 20% of ad budget to Klaviyo email list retention, and raise free-shipping threshold from $50 to $60."
            },
            {
                "head": "Fragrance Supplier Backorder Inventory Lock",
                "problem": "Raw fragrance supplier backorder temporarily knocked out 9 top-selling SKUs for 14 days, causing an estimated $2,400 in unfulfilled Shopify orders.",
                "solution": "Diversify primary fragrance oil supplier and establish a 30-day raw material safety buffer before Q4 production."
            }
        ],
        "opportunities": [
            {
                "head": "Klaviyo Email Retention & Subscription Box",
                "body": "Shift acquisition dependency from paid ads to Klaviyo email sequences to hit 40% email revenue share goal ahead of Q4."
            }
        ],
        "what_changed": [
            "ROAS fatigue reduced net contribution margin from 38% to 28.5%.",
            "Email marketing share rose to 34% of monthly DTC orders."
        ],
        "missing_data_notice": None
    },

    # 2. INSIGHTS MODE PAYLOAD
    "insights_mode": {
        "profitability_banner": {
            "status": "at_average",
            "headline": "71% gross margin pre-ad; ad acquisition efficiency is primary margin lever.",
            "supporting_text": "Contribution margin at 28.5% post-ad; Q4 holiday pre-production ramp is on schedule.",
            "missing_data_notice": None
        },
        "items": [
            {
                "signal_id": "ad_roas_fatigue",
                "pressing_score": 84,
                "tier": "tier_1",
                "headline": "Meta Ad ROAS Slid 3.4 -> 2.4 ($1,850/mo Margin Squeeze)",
                "whats_going_on": "Shopify + Meta ads integration shows customer acquisition cost (CAC) rose from $15.80 to $22.50 per customer, lowering ROAS to 2.4 on $4,200 monthly spend.",
                "why_it_matters_now": "Unchecked ad fatigue erodes net cash contribution prior to scaling ad budgets to $9,000/mo in Q4.",
                "what_to_do": "Rotate ad creative, test UGC video formats, and lift Average Order Value (AOV) above $60 via free-shipping threshold rules.",
                "expected_impact": {
                    "value_text": "+$1,850/mo contribution recovered",
                    "calculation_basis": "Restoring ROAS back to 3.2+ recovers $1,850/mo in net marketing contribution."
                },
                "effort": "quick_win",
                "confidence": "high",
                "directive": {
                    "shape_id": "roas_decay_chart",
                    "state": "active",
                    "theme": "critical",
                    "numbers": {"previous_roas": 3.4, "current_roas": 2.4, "target_roas": 3.2},
                    "labels": {"previous": "Initial ROAS", "current": "Current ROAS", "target": "Target Goal"}
                }
            }
        ],
        "missing_data_notice": None
    },

    # 3. DRAWER MODE PAYLOAD
    "drawer_mode": {
        "revenue": {
            "value_text": "$29,000",
            "status_badge": {"label": "Q4 Ramp", "severity": "above_average"},
            "headline_read": "DTC sales steady at $29.0K MTD; 45% Meta ad-driven, 30% email, 25% organic.",
            "benchmarks": {
                "peer_avg": "$24,500/mo",
                "sba_metric": "Above average for DTC home fragrance brands",
                "position": "above",
                "gap_text": "18.3% above regional e-commerce benchmark"
            },
            "drivers": [
                {"description": "Meta ad-driven purchases (45% share)", "impact": "+$13,050", "category": "Paid Social"},
                {"description": "Klaviyo email campaign orders (30% share)", "impact": "+$8,700", "category": "Email Marketing"},
                {"description": "Direct & organic search sales (25% share)", "impact": "+$7,250", "category": "Organic"}
            ],
            "actions": [
                {"description": "Raise free-shipping threshold from $50 to $60 to lift AOV", "priority": "high", "effort": "quick_win"}
            ]
        }
    },

    # 4. DEMAND FORECAST PAYLOAD
    "demand_forecast": {
        "metrics": {
            "forecast_series": [14500.0, 15950.0, 20300.0, 21750.0, 24650.0, 23200.0, 21750.0, 24650.0, 31900.0, 40600.0, 60900.0, 55100.0]
        },
        "flags": [
            {"severity": "red", "title": "Meta Ad ROAS Slide (3.4 -> 2.4)"},
            {"severity": "amber", "title": "USPS Postal Shipping Hike (+6%)"}
        ],
        "data": {
            "historical_revenue": [
                {"date": "2026-01-01", "amount": 14500.0},
                {"date": "2026-02-01", "amount": 15950.0},
                {"date": "2026-03-01", "amount": 20300.0},
                {"date": "2026-04-01", "amount": 29000.0}
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
                        "headline": "Projected weekend e-commerce sales of $4,800 across Shopify store orders.",
                        "expected_value": "$4,800",
                        "expected_unit": "revenue",
                        "volume_forecast": 92,
                        "demand_unit": "Orders",
                        "confidence_pct": 89,
                        "confidence_label": "High",
                        "anchor": "Anchored in Shopify Analytics weekend checkout conversion & Klaviyo email flows."
                    },
                    "swing_factor": {
                        "headline": "Sunday Evening Email Campaign (+18% conversion)",
                        "delta_text": "+$950",
                        "direction": "up",
                        "reasoning": "Automated Sunday night flash sale broadcast targeting VIP subscriber list."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "Queue Klaviyo Sunday 7 PM broadcast & check 3PL weekend inventory", "severity": "above_average"},
                        "whats_moving": {"summary": "2 key demand drivers (Klaviyo email campaign, TikTok organic video viral spike)", "severity": "above_average"},
                        "breakdown": {"summary": "60% organic/email, 28% Meta Ads, 12% affiliate referrals", "severity": "above_average"},
                        "track_record": {"summary": "DTC weekend forecast accuracy ran within 2.5% over past 4 weekends", "severity": "above_average"},
                        "world_scan": {"summary": "Sunday night online shopping traffic peak expected at 8 PM EST", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_ecomm_email_01",
                            "action": "Schedule Klaviyo VIP flash sale broadcast for Sunday 7 PM EST",
                            "deadline": "Sun, Feb 9",
                            "priority": "high",
                            "tied_to_driver": "Sunday Evening Email Campaign",
                            "why_this_much": "Captures peak Sunday night online shopper traffic.",
                            "dollar_logic": "Generates +$950 in direct high-margin store orders."
                        }
                    ],
                    "whats_moving": [
                        {
                            "name": "Sunday Evening Email Campaign",
                            "window": "This Weekend",
                            "severity": "green",
                            "impact_text": "+$950",
                            "reasoning": "Proven high open-rate email segment driving immediate checkout orders.",
                            "source": "Klaviyo Analytics",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 3200.0,
                        "expected_losses": 120.0,
                        "unbooked_demand": 1720.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "DTC store predictions hit within 2.5% accuracy.",
                        "lean_guidance": "High accuracy on scheduled email marketing pushes."
                    },
                    "world_scan": [
                        {
                            "flag": "USPS Weekend Fulfillment Shift",
                            "horizon": "Saturday 12 PM Pickup",
                            "depends_on": "3PL warehouse packing speed",
                            "action_yet": "Batch print labels by 10 AM Saturday",
                            "source": "Shopify Shipping Manager"
                        }
                    ]
                },
                {
                    "window": "Next 30 Days",
                    "severity": "amber",
                    "hero": {
                        "eyebrow": "Forward Demand Read",
                        "headline": "DTC order demand tracking at $29,000 MTD; ad fatigue optimization is key contribution lever.",
                        "expected_value": "$29,000",
                        "expected_unit": "revenue",
                        "confidence_pct": 84,
                        "confidence_label": "High",
                        "anchor": "Anchored in Shopify DTC storefront actuals + Klaviyo email campaign engagement logs."
                    },
                    "swing_factor": {
                        "headline": "Meta ad acquisition cost increase (ROAS 2.4)",
                        "delta_text": "-$1,850",
                        "direction": "down",
                        "reasoning": "Ad fatigue increased CAC from $15.80 to $22.50 per customer."
                    },
                    "section_summaries": {
                        "do_this": {"summary": "2 actions to rotate Meta ad creative and raise free-shipping threshold to $60", "severity": "below_average"},
                        "whats_moving": {"summary": "3 DTC drivers (Meta paid social, Klaviyo VIP email, organic search)", "severity": "above_average"},
                        "breakdown": {"summary": "45% Meta ads, 30% Klaviyo email, 25% organic DTC", "severity": "above_average"},
                        "track_record": {"summary": "Prior 90-day forecast ran within 4.4% of actual Shopify revenue", "severity": "above_average"},
                        "world_scan": {"summary": "USPS shipping rates up 6%; holiday gift demand building", "severity": "above_average"}
                    },
                    "actions": [
                        {
                            "id": "act_ecomm_1",
                            "title": "Raise Shopify free-shipping threshold from $50 to $60 to lift AOV",
                            "deadline": "Feb 15",
                            "priority": "high",
                            "tied_to_driver": "ROAS Fatigue Squeeze",
                            "why_this_much": "Lifts Average Order Value by $6.00 to offset higher acquisition CAC.",
                            "dollar_logic": "+$1,850/mo contribution recovered"
                        },
                        {
                            "id": "act_ecomm_2",
                            "title": "Rotate Meta ad video creative and shift 20% budget to Klaviyo email retention",
                            "deadline": "Feb 22",
                            "priority": "medium",
                            "tied_to_driver": "ROAS Fatigue Squeeze",
                            "why_this_much": "Restores ROAS to 3.2+ baseline before scaling ad spend in Q4.",
                            "dollar_logic": "+$2,400/mo ad spend efficiency"
                        }
                    ],
                    "drivers": [
                        {
                            "name": "ROAS Fatigue Squeeze",
                            "severity": "red",
                            "window": "Next 30 Days",
                            "impact_text": "-$1,850",
                            "reasoning": "ROAS slid to 2.4 on $4,200 ad spend.",
                            "source": "Meta Ads Manager",
                            "confidence": "high"
                        },
                        {
                            "name": "USPS Rate Increase",
                            "severity": "amber",
                            "window": "Next 30 Days",
                            "impact_text": "-$380",
                            "reasoning": "6% postage rate hike across parcel shipping.",
                            "source": "Fulfillment Logs",
                            "confidence": "high"
                        }
                    ],
                    "breakdown": {
                        "committed": 13050.0,
                        "expected_losses": 1850.0,
                        "unbooked_demand": 17800.0,
                        "external_adjustment": 0.0
                    },
                    "track_record": {
                        "accuracy_receipt": "Prior 90-day forecast ran within 4.4% of actual Shopify storefront revenue.",
                        "lean_guidance": "Slight conservative bias on email blast conversion spikes."
                    },
                    "world_scan": [
                        {
                            "flag": "USPS Postal Rate Adjustment",
                            "horizon": "Feb-Mar",
                            "depends_on": "Package weight and shipping zone distribution",
                            "action_yet": "Audit regional fulfillment carrier options",
                            "source": "Logistics Industry Scan"
                        }
                    ]
                }
            ]
        }
    },

    # 5. BUSINESS HEALTH PAYLOAD
    "business_health": {
        "overall_score": 77,
        "status": "Healthy",
        "dimensions": {
            "liquidity": {"score": 75, "label": "Good", "cash_months": 7.2},
            "profitability": {"score": 72, "label": "Moderate", "net_margin": 14.2},
            "growth": {"score": 88, "label": "High", "yoy_growth": 14.2},
            "efficiency": {"score": 70, "label": "Needs Action", "roas_efficiency": "2.4 ROAS"},
            "resilience": {"score": 80, "label": "Solid", "debt_load": "$0 (No Loan)"}
        }
    },

    # 6. BUSINESS PROFILE PAYLOAD
    "business_profile": {
        "section_1_basics": {
            "business_name": "Lakeshore Candle Co.",
            "legal_entity": "Kowalski Fragrance LLC",
            "year_founded": 2020,
            "headquarters": "Grand Rapids, MI",
            "website": "https://lakeshorecandleco.com",
            "operating_mode": "DTC E-Commerce & Subscription Box"
        },
        "section_2_ownership": {
            "owner_name": "Erin Kowalski",
            "ownership_pct": 100.0,
            "role": "Founder & Brand Director",
            "years_in_business": 6
        },
        "section_3_industry": {
            "primary_industry": "Direct-to-Consumer E-Commerce & Home Goods",
            "naics_code": "454110",
            "niche": "Hand-Poured Soy Wax Candles & Home Fragrance"
        },
        "section_4_operations": {
            "days_open_per_week": 7,
            "operating_hours": "24/7 E-Commerce Storefront",
            "pos_system": "Shopify Plus",
            "email_platform": "Klaviyo"
        },
        "section_5_financial": {
            "annual_revenue": 348000.0,
            "gross_margin_pct": 71.0,
            "net_margin_pct": 14.2,
            "monthly_cash_flow": 4118.0,
            "accounting_software": "QuickBooks Online"
        },
        "section_6_assets": {
            "real_estate": "Leased studio workshop (1,500 sq ft)",
            "equipment_value": 28000.0,
            "inventory_valuation": 32000.0
        },
        "section_7_customers": {
            "customer_type": "B2C E-Commerce Shoppers",
            "average_ticket": 52.0,
            "monthly_transacting_customers": 558
        },
        "section_8_risk": {
            "top_cost_exposure": "Meta Ad Acquisition CAC Increase (ROAS 2.4)",
            "capacity_risk": "Fragrance oil supplier backorder"
        },
        "section_9_capacity": {
            "monthly_candle_pour_capacity": 4000,
            "current_production_capacity_pct": 65.0
        },
        "section_10_opportunity_readiness": {
            "subscription_engine": "Active (Recharge + Shopify)",
            "email_subscribers_count": 14200
        },
        "section_11_goals": {
            "target_annual_revenue": 450000.0,
            "margin_target": 18.0,
            "growth_focus": "Klaviyo email retention & Q4 holiday bundling"
        },
        "section_12_pricing": {
            "pricing_tier": "DTC Premium",
            "price_points": {"8oz_soy_candle": "$26", "diffuser": "$34", "trio_bundle": "$68"}
        },
        "section_13_team": {
            "full_time_staff": 2,
            "part_time_staff": 2,
            "key_personnel": "Founder, Production Lead, Fulfillment Manager"
        },
        "section_14_marketing": {
            "primary_channels": "Meta Ads (Instagram/FB), Klaviyo Email, Pinterest",
            "monthly_ad_budget": 4200.0
        },
        "section_15_owner_prefs": {
            "risk_tolerance": "Moderate",
            "funding_preference": "Reinvest profits, zero debt"
        },
        "section_16_docs": {
            "connected_systems": ["Shopify Plus", "Klaviyo", "QuickBooks Online", "Meta Ads"],
            "verification_status": "Verified"
        }
    },

    # 7. OPPORTUNITIES V2 PAYLOAD
    "opportunities": {
        "kpis": {
            "active_opportunities": {"count": 6, "descriptor": "Browse DTC matches"},
            "new_this_week": {"count": 2, "label": "2 new this week"},
            "total_potential_value": "$21,400",
            "avg_fit_score": 87,
            "event_readiness_index": 84,
            "historical_roi": {"multiplier": "2.9x", "sample_size": 4}
        },
        "recommended_hero": {
            "id": "opp_ecomm_hero",
            "type": "Vendor Program",
            "box_type": "Direct Match",
            "out_box": False,
            "title": "Shopify Collective Brand Partnership & Cross-Store Catalog",
            "source": "Shopify Merchant Network",
            "match_score": 91,
            "readiness_score": 87,
            "data_trust_indicator": "Verified",
            "risk_level": "Low",
            "drive_time_minutes": 0,
            "distance_miles": 0,
            "expires_at": "Closes in 20 days",
            "estimated_revenue": "$9,500/mo",
            "listed_fee": "$0 (Shopify Native)",
            "why_reason_codes": ["Cross-sells soy candles on high-traffic home decor Shopify stores without ad spend"],
            "risk_signals": ["Requires 20% wholesale margin split"],
            "verify_flag": False,
            "verify_flag_message": None,
            "registration_url": "https://shopify.com/collective/join",
            "source_url": "https://shopify.com/collective"
        },
        "more_matches": [],
        "recommended": [
            {
                "id": "opp_ecomm_1",
                "title": "Klaviyo Email Retention & Subscription Box",
                "impact": "+$4,200/mo recurring revenue",
                "strategic_fit": "Reduces dependency on paid Meta ad acquisition",
                "execution_steps": [
                    "Build automated post-purchase candle care email sequence",
                    "Offer 15% discount on quarterly candle subscription refills"
                ],
                "risk_rating": "Low"
            }
        ],
        "selected_tracked": [
            {
                "id": "track_ecomm_1",
                "title": "Shopify Collective Brand Partnership",
                "type": "Vendor Program",
                "status": "Tracked",
                "estimated_revenue": "$9,500/mo",
                "next_checkpoint": "Day 3 check-in in 2 days"
            }
        ],
        "portfolio_summary": {
            "active_count": 1,
            "past_count": 4,
            "total_committed_dollars": "$9,500"
        }
    },

    # 8. SCENARIOS PAYLOAD
    "scenarios": {
        "scenario_id": "scen_ecomm_sub",
        "confidence": 88,
        "risk": "Low",
        "impact_cards": [
            {"label": "Email Orders Lift", "value": "+$4,200", "direction": "up"},
            {"label": "ROAS Efficiency Rebound", "value": "+0.8 ROAS", "direction": "up"},
            {"label": "Contribution Margin Lift", "value": "+3.4%", "direction": "up"}
        ]
    }
}
