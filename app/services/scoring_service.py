from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ScoringService:

    def __init__(self):
        self.high_prestige_events = ["premium", "elite"]

    def _safe_float(self, value: Any) -> float:

        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:

        if not value:
            return None

        try:
            return datetime.fromisoformat(value.replace("Z", ""))
        except Exception:
            return None

    def calculate_match_score(self, opportunity: Dict[str, Any], business_context: Dict[str, Any]) -> int:

        score = 0

        business_tags = set(opportunity.get("business_tags", []))
        opportunity_tags = set(opportunity.get("opportunity_tags", []))
        business_classifications = set(business_context.get("business_classifications", []))
        service_fit = set(opportunity.get("event_service_fit", []))
        proven_capabilities = set(opportunity.get("proven_capabilities", []))

        audience = opportunity.get("audience")
        event_audience = opportunity.get("event_audience")

        opportunity_type = opportunity.get("type", "").lower().strip()
        prestige = opportunity.get("event_prestige_tier", "unknown")

        jaccard_score = float(opportunity.get("industry_jaccard_score", 0))
        adjacent_match = opportunity.get("adjacent_match", False)

        score += int(jaccard_score * 35)

        if adjacent_match:
            score += 8

        overlap_count = len(business_tags.intersection(opportunity_tags))
        score += min(overlap_count * 4, 20)

        capability_overlap = len(proven_capabilities.intersection(service_fit))
        score += min(capability_overlap * 6, 18)

        if audience and event_audience and audience == event_audience:
            score += 10

        if "food_hospitality" in business_classifications and opportunity_type == "event":
            score += 10

        if "solo_operator" in business_classifications and opportunity_type in ["rfp", "supplier"]:
            score -= 18

        if "established_smb" in business_classifications and opportunity_type in ["rfp", "supplier"]:
            score += 15

        if "product_business" in business_classifications and opportunity_type in ["placement", "platform", "export"]:
            score += 12

        if "service_business" in business_classifications and opportunity_type in ["placement", "platform"]:
            score -= 12

        if prestige == "elite":
            score += 10

        elif prestige == "premium":
            score += 6

        if opportunity_type == "grant":
            score += 4

        if opportunity_type == "training":
            score += 2

        return max(0, min(score, 100))

    def calculate_readiness_score(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> int:

        forward_looking_cash = self._calculate_forward_looking_cash_score(opportunity, business_context)

        capacity_demand_strain = self._calculate_capacity_demand_strain_score(opportunity, business_context)

        timing_vs_complexity = self._calculate_timing_vs_complexity_score(opportunity)

        permit_logistics = self._calculate_permit_logistics_score(opportunity, business_context)

        total_score = (
            forward_looking_cash
            + capacity_demand_strain
            + timing_vs_complexity
            + permit_logistics
        )

        return max(0, min(total_score, 100))
    
    def calculate_portfolio_adjusted_readiness(
        self,
        opportunity: Dict[str, Any],
        readiness_score: int,
    ) -> int:

        overlapping_commitments = int(opportunity.get("portfolio_overlap_count", 0) or 0)
        
        adjustment = overlapping_commitments * 5

        adjusted_score = readiness_score - adjustment

        return max(0, adjusted_score)

    def _calculate_forward_looking_cash_score(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> int:

        listed_fee = self._safe_float(opportunity.get("listed_fee") or opportunity.get("cost"))

        if listed_fee <= 0:
            return 25

        start_date = self._parse_date(opportunity.get("start_date") or opportunity.get("date"))
        deadline = self._parse_date(opportunity.get("deadline"))

        relevant_date = start_date

        if deadline and start_date and deadline < start_date:
            relevant_date = deadline
        elif deadline and not start_date:
            relevant_date = deadline

        cash_balance = self._safe_float(business_context.get("cash_balance"))
        outstanding_ar = business_context.get("outstanding_ar", [])

        qualifying_ar = 0

        for ar in outstanding_ar:

            ar_amount = self._safe_float(ar.get("amount"))
            receipt_date = self._parse_date(ar.get("expected_receipt_date"))

            if relevant_date and receipt_date and receipt_date <= relevant_date:
                qualifying_ar += ar_amount

        effective_cash = cash_balance + qualifying_ar

        runway_trend = (business_context.get("runway_trend", "stable") or "stable").lower()

        if runway_trend == "improving":
            effective_cash *= 1.10
        elif runway_trend == "declining":
            effective_cash *= 0.90

        cash_ratio = effective_cash / max(listed_fee, 1)

        if cash_ratio >= 5:
            return 25
        if cash_ratio >= 3:
            return 20
        if cash_ratio >= 2:
            return 15
        if cash_ratio >= 1:
            return 8

        return 2
    
    def _calculate_capacity_demand_strain_score(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> int:

        start_date = self._parse_date(opportunity.get("start_date") or opportunity.get("date"))

        if not start_date:
            return 15

        days_until = (start_date - datetime.utcnow()).days

        # Retrieve the handoff forecast object
        handoff = business_context.get("latest_demand_forecast")
        if not handoff or not isinstance(handoff, dict):
            # Fallback to checking the retired scalars for backward compatibility
            strain = None

            if days_until <= 30:
                strain = business_context.get("demand_strain_next_30d")

            elif days_until <= 60:
                strain = business_context.get("demand_strain_next_60d")

            elif days_until <= 90:
                strain = business_context.get("demand_strain_next_90d")

            if strain is None:
                return 15

            strain = self._safe_float(strain)

            if strain < 0.08:
                return 25

            if strain < 0.15:
                return 20

            if strain < 0.25:
                return 12

            if strain < 0.35:
                return 6

            return 2

        # Extract level from handoff object
        level = handoff.get("level", "steady")

        # Try to find a more specific window if possible
        windows = handoff.get("windows", [])
        matched_window = None
        for w in windows:
            w_name = w.get("window", "").lower()
            if days_until <= 7 and ("weekend" in w_name or "week" in w_name or "current" in w_name or "this" in w_name):
                matched_window = w
                break
            elif days_until <= 30 and ("month" in w_name or "30" in w_name):
                matched_window = w
                break
            elif days_until <= 60 and ("60" in w_name or "2 months" in w_name or "next month" in w_name):
                matched_window = w
                break
            elif days_until <= 90 and ("90" in w_name or "quarter" in w_name or "3 months" in w_name):
                matched_window = w
                break

        if matched_window:
            level = matched_window.get("level", level)

        # Map the text level/severity to score
        # Elevated/high demand -> high strain -> low favorability (6 or 2)
        # Steady/neutral/normal demand -> medium strain -> medium favorability (15 or 12)
        # Soft/low demand -> low strain -> high favorability (20 or 25)
        level_str = str(level).lower().strip()
        if any(keyword in level_str for keyword in ["soft", "low", "weak", "green"]):
            return 25
        elif any(keyword in level_str for keyword in ["elevated", "high", "busy", "pressing", "red"]):
            return 6
        elif any(keyword in level_str for keyword in ["watch", "amber"]):
            return 12
        else:  # steady, flat, normal, white, etc.
            return 15

    def _calculate_timing_vs_complexity_score(
        self,
        opportunity: Dict[str, Any],
    ) -> int:

        opportunity_type = (opportunity.get("type") or "").lower()

        target_date = (
            self._parse_date(opportunity.get("registration_deadline"))
            or self._parse_date(opportunity.get("deadline"))
            or self._parse_date(opportunity.get("start_date"))
            or self._parse_date(opportunity.get("date"))
        )

        if not target_date:
            return 15

        days_until = (target_date - datetime.utcnow()).days

        required_days = {
            "event": 21,
            "grant": 14,
            "rfp": 30,
            "privatecontract": 14,
            "award": 7,
            "placement": 14,
            "vendorprogram": 14,
            "govcertification": 0,
            "venueresidency": 14,
            "coopprogram": 7,
            "accelerator": 21,
            "platformwindow": 7,
            "exportprogram": 14,
        }

        minimum_days = required_days.get(opportunity_type, 14)

        if opportunity_type == "govcertification":
            return 25

        if days_until >= minimum_days:
            return 25

        if days_until >= int(minimum_days * 0.7):
            return 18

        if days_until >= int(minimum_days * 0.4):
            return 10

        return 2

    def _calculate_permit_logistics_score(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> int:

        permits_required = (
            opportunity.get("risk_signals", {}).get("listed_permit_requirements", [])
        )

        if not permits_required:
            return 25

        existing_permits = set(
            business_context.get("permits_and_licenses", [])
        )

        processing_times = {
            "health department": 14,
            "food handler": 14,
            "temporary food establishment permit": 10,
            "seller permit": 5,
            "sales tax permit": 5,
            "business license": 5,
            "fire marshal": 7,
            "safety inspection": 7,
        }

        longest_processing_time = 0

        for permit in permits_required:

            permit_lower = permit.lower()

            if permit_lower in existing_permits:
                continue

            for key, days in processing_times.items():

                if key in permit_lower:
                    longest_processing_time = max(longest_processing_time, days)

        if longest_processing_time == 0:
            return 25

        target_date = (
            self._parse_date(opportunity.get("deadline"))
            or self._parse_date(opportunity.get("start_date"))
            or self._parse_date(opportunity.get("date"))
        )

        if not target_date:
            return 15

        days_until = (target_date - datetime.utcnow()).days

        if days_until < longest_processing_time:
            return 0

        if days_until >= longest_processing_time * 2:
            return 25

        return 12

    def calculate_event_readiness_score(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> Optional[int]:

        opportunity_type = (opportunity.get("type") or "").lower().strip()

        if opportunity_type != "event":
            return None

        time_readiness = self._calculate_event_time_readiness(opportunity)

        weather_readiness = self._calculate_event_weather_readiness(opportunity)

        financial_readiness = self._calculate_event_financial_readiness(
            opportunity,
            business_context,
        )

        operational_readiness = self._calculate_event_operational_readiness(
            opportunity,
            business_context,
        )

        total_score = (
            time_readiness
            + weather_readiness
            + financial_readiness
            + operational_readiness
        )

        return max(0, min(total_score, 100))

    def calculate_event_readiness_label(
        self,
        event_readiness_score: Optional[int],
    ) -> Optional[str]:

        if event_readiness_score is None:
            return None

        if event_readiness_score >= 85:
            return "Optimal conditions"

        if event_readiness_score >= 70:
            return "Favorable conditions"

        if event_readiness_score >= 55:
            return "Moderate conditions"

        if event_readiness_score >= 40:
            return "Challenging conditions"

        return "Difficult conditions"

    def calculate_expected_roi(
        self,
        opportunity: Dict[str, Any],
    ) -> Dict[str, Any]:

        estimated_revenue = self._safe_float(
            opportunity.get("estimated_revenue")
            or opportunity.get("est_revenue")
        )

        estimated_cost = self._safe_float(
            opportunity.get("estimated_cost")
            or opportunity.get("cost")
        )

        if estimated_revenue <= 0 or estimated_cost <= 0:

            return {
                "expected_roi_mult": None,
                "expected_roi_display": "ROI not available",
            }

        profit_est = estimated_revenue - estimated_cost

        expected_roi_mult = round(
            profit_est / max(estimated_cost, 1),
            1,
        )

        opportunity_type = (
            opportunity.get("type")
            or ""
        ).lower().strip()

        time_display = self._calculate_roi_time_horizon(
            opportunity,
        )

        roi_prefix = ""

        if opportunity_type == "grant":
            roi_prefix = "~"

        return {
            "expected_roi_mult": expected_roi_mult,
            "expected_roi_display": (
                f"{roi_prefix}{expected_roi_mult}x over {time_display}"
            ),
        }

    def generate_why_reason_codes(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
        match_score: int,
    ) -> list:

        codes = []

        distance_miles = self._safe_float(
            opportunity.get("distance_miles")
        )

        drive_time_minutes = self._safe_float(
            opportunity.get("drive_time_minutes")
        )

        if distance_miles and distance_miles <= 10:

            codes.append({
                "code": "LOCAL_MATCH",
                "data": {
                    "distance_miles": round(distance_miles, 1),
                },
            })

        elif drive_time_minutes and drive_time_minutes <= 15:

            codes.append({
                "code": "LOCAL_MATCH",
                "data": {
                    "drive_time_minutes": int(drive_time_minutes),
                },
            })

        tag_match_score = int(
            opportunity.get("tag_match_score", 0)
        )

        if tag_match_score == 15:

            codes.append({
                "code": "STRONG_INDUSTRY_MATCH",
                "data": {
                    "primary_tag": (
                        opportunity.get("primary_tag")
                        or (
                            opportunity.get("business_tags", [None])[0]
                        )
                    ),
                },
            })

        elif 9 <= tag_match_score < 15:

            codes.append({
                "code": "INDUSTRY_MATCH",
                "data": {
                    "sub_industry": (
                        opportunity.get("sub_industry")
                        or (
                            opportunity.get("business_tags", [None])[0]
                        )
                    ),
                    "tag_match_score": tag_match_score,
                },
            })

        historical_outcomes = business_context.get(
            "historical_outcomes",
            [],
        )

        matching_outcomes = [
            item
            for item in historical_outcomes
            if item.get("type") == opportunity.get("type")
        ]

        if len(matching_outcomes) >= 2:

            roi_values = [
                self._safe_float(item.get("roi"))
                for item in matching_outcomes
                if item.get("roi") is not None
            ]

            if roi_values:

                avg_roi = round(
                    sum(roi_values) / len(roi_values),
                    1,
                )

                if avg_roi > 2.0:

                    codes.append({
                        "code": "PEER_ROI_HIGH",
                        "data": {
                            "avg_roi": avg_roi,
                            "sample_n": len(roi_values),
                        },
                    })

        prior_success = next(
            (
                item
                for item in matching_outcomes
                if self._safe_float(item.get("roi")) > 0
            ),
            None,
        )

        if prior_success:

            codes.append({
                "code": "MATCHES_PAST_SUCCESS",
                "data": {
                    "prior_roi": self._safe_float(
                        prior_success.get("roi")
                    ),
                },
            })

        weather_snapshot = (
            opportunity.get("weather_data", {})
            .get("weather_snapshot", {})
        )

        outdoor_flag = opportunity.get("outdoor_flag")

        precipitation_probability = self._safe_float(
            weather_snapshot.get("precipitation_probability")
        )

        temperature_comfort_score = self._safe_float(
            weather_snapshot.get("temperature_comfort_score")
        )

        severe_weather_flag = weather_snapshot.get(
            "severe_weather_flag",
            False,
        )

        if (
            outdoor_flag is True
            and precipitation_probability < 0.10
            and temperature_comfort_score > 0.6
            and not severe_weather_flag
        ):

            codes.append({
                "code": "WEATHER_FAVORABLE",
                "data": {
                    "precipitation_probability": precipitation_probability,
                },
            })

        if match_score >= 80:

            codes.append({
                "code": "HIGH_FIT_SCORE",
                "data": {
                    "match_score": match_score,
                },
            })

        listed_fee = self._safe_float(
            opportunity.get("listed_fee")
            or opportunity.get("cost")
        )

        cash_balance = self._safe_float(
            business_context.get("cash_balance")
        )

        outstanding_ar = business_context.get(
            "outstanding_ar",
            [],
        )

        qualifying_ar = sum(
            self._safe_float(item.get("amount"))
            for item in outstanding_ar
        )

        effective_cash = cash_balance + qualifying_ar

        cash_ratio = effective_cash / max(listed_fee, 1)

        if cash_ratio >= 3:

            codes.append({
                "code": "AFFORDABLE",
                "data": {
                    "cash_ratio": round(cash_ratio, 1),
                },
            })

        target_date = (
            self._parse_date(opportunity.get("deadline"))
            or self._parse_date(opportunity.get("start_date"))
            or self._parse_date(opportunity.get("date"))
        )

        if target_date:

            days_to_deadline = max(
                (target_date - datetime.utcnow()).days,
                0,
            )

            timing_fit = self._calculate_timing_vs_complexity_score(
                opportunity,
            )

            if timing_fit >= 20:

                codes.append({
                    "code": "TIMING_GOOD",
                    "data": {
                        "days_to_deadline": days_to_deadline,
                    },
                })

        if opportunity.get("box_type") == "out_box":

            codes.append({
                "code": "OUT_OF_BOX_MATCH",
                "data": {
                    "asset_used": opportunity.get("asset_used"),
                },
            })

        credibility_summary = (
            opportunity.get("credibility_summary")
            or ""
        ).lower()

        years_running = int(
            opportunity.get("years_running", 0) or 0
        )

        if (
            credibility_summary == "high"
            and years_running >= 3
        ):

            codes.append({
                "code": "VERIFIED_SOURCE",
                "data": {
                    "years_running": years_running,
                },
            })

        service_model = business_context.get(
            "service_model"
        )

        price_tier = business_context.get(
            "price_tier"
        )

        event_service_fit = opportunity.get(
            "event_service_fit",
            [],
        )

        prestige_tier = opportunity.get(
            "event_prestige_tier"
        )

        if (
            service_model
            and price_tier
            and service_model in event_service_fit
            and price_tier == prestige_tier
        ):

            codes.append({
                "code": "SERVICE_MODEL_MATCH",
                "data": {
                    "service_model": service_model,
                    "price_tier": price_tier,
                },
            })

        business_audience = (
            business_context.get("audience")
        )

        event_audience = (
            opportunity.get("event_audience")
        )

        if (
            business_audience
            and event_audience
            and business_audience == event_audience
            and business_audience != "hybrid"
        ):

            codes.append({
                "code": "AUDIENCE_MATCH",
                "data": {
                    "audience": business_audience,
                },
            })

        return codes

    def _calculate_roi_time_horizon(
        self,
        opportunity: Dict[str, Any],
    ) -> str:

        opportunity_type = (
            opportunity.get("type")
            or ""
        ).lower().strip()

        now = datetime.utcnow()

        if opportunity_type == "event":

            start_date = (
                self._parse_date(opportunity.get("start_date"))
                or self._parse_date(opportunity.get("date"))
            )

            end_date = self._parse_date(opportunity.get("end_date"))

            if not start_date:
                return "~unknown duration"

            prep_days = max((start_date - now).days, 0)

            duration_days = 1

            if end_date:
                duration_days = max(
                    (end_date - start_date).days,
                    1,
                )

            total_days = prep_days + duration_days

            return f"{total_days} days"

        if opportunity_type == "grant":

            source_name = (
                opportunity.get("source_name")
                or opportunity.get("provider")
                or ""
            ).lower()

            federal_keywords = [
                "sba",
                "federal",
                "usda",
                "hud",
                "u.s. department",
            ]

            local_keywords = [
                "city of",
                "county of",
                "texas",
                "california",
                "florida",
                "new york",
            ]

            estimated_days = 120

            if any(keyword in source_name for keyword in federal_keywords):
                estimated_days = 180

            elif any(keyword in source_name for keyword in local_keywords):
                estimated_days = 90

            elif ".gov" in source_name:
                estimated_days = 180

            months = round(estimated_days / 30)

            return f"~{months} months"

        deadline = (
            self._parse_date(opportunity.get("deadline"))
            or self._parse_date(opportunity.get("registration_deadline"))
        )

        if deadline:

            days_until = max(
                (deadline - now).days,
                1,
            )

            return f"{days_until} days"

        return "~unknown duration"

    def _calculate_event_time_readiness(
        self,
        opportunity: Dict[str, Any],
    ) -> int:

        target_date = (
            self._parse_date(opportunity.get("start_date"))
            or self._parse_date(opportunity.get("date"))
        )

        if not target_date:
            return 15

        days_until = (target_date - datetime.utcnow()).days

        if days_until >= 28:
            return 25

        if days_until >= 21:
            return 22

        if days_until >= 14:
            return 18

        if days_until >= 7:
            return 12

        if days_until >= 3:
            return 6

        return 2

    def _calculate_event_weather_readiness(
        self,
        opportunity: Dict[str, Any],
    ) -> int:

        weather_data = opportunity.get("weather_data", {})
        weather_snapshot = weather_data.get("weather_snapshot", {})

        if not weather_snapshot:
            return 15

        outdoor_flag = opportunity.get("outdoor_flag")

        precipitation_probability = self._safe_float(
            weather_snapshot.get("precipitation_probability")
        )

        temperature_comfort_score = self._safe_float(
            weather_snapshot.get("temperature_comfort_score")
        )

        severe_weather_flag = weather_snapshot.get(
            "severe_weather_flag",
            False,
        )

        if outdoor_flag is True:

            if (
                precipitation_probability < 0.10
                and temperature_comfort_score > 0.6
                and not severe_weather_flag
            ):
                return 22

            if (
                0.10 <= precipitation_probability <= 0.30
                and not severe_weather_flag
            ):
                return 16

            if 0.30 <= precipitation_probability <= 0.50:
                return 10

            return 4

        if outdoor_flag is False:

            if severe_weather_flag:
                return 8

            return 25

        if severe_weather_flag:
            return 8

        return 18

    def _calculate_event_financial_readiness(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> int:

        listed_fee = self._safe_float(
            opportunity.get("listed_fee") or opportunity.get("cost")
        )

        if listed_fee <= 0:
            return 25

        effective_cash_score = self._calculate_forward_looking_cash_score(
            opportunity,
            business_context,
        )

        mapping = {
            25: 25,
            20: 22,
            15: 18,
            8: 10,
            2: 5,
        }

        return mapping.get(effective_cash_score, 15)

    def _calculate_event_operational_readiness(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> int:

        strain_score = self._calculate_capacity_demand_strain_score(
            opportunity,
            business_context,
        )

        mapping = {
            25: 25,
            20: 20,
            12: 14,
            6: 8,
            2: 8,
            15: 15,
        }

        return mapping.get(strain_score, 15)

    def calculate_data_trust_indicator(self, opportunity: Dict[str, Any]) -> str:

        extraction_confidence = float(opportunity.get("extraction_confidence", 0))
        credibility_summary = opportunity.get("credibility_summary", "unverified")
        verify_flag = bool(opportunity.get("verify_flag", False))

        if extraction_confidence >= 0.80 and credibility_summary == "high":
            return "Verified"

        if extraction_confidence < 0.50 or credibility_summary == "unverified" or verify_flag:
            return "Needs Review"

        return "Unverified"

    def build_score_history_entry(
        self,
        match_score: int,
        readiness_score: int,
        event_readiness_score: Optional[int],
        trigger: str,
    ) -> Dict[str, Any]:

        return {
            "scored_at": datetime.utcnow().isoformat(),
            "match_score": match_score,
            "readiness_score": readiness_score,
            "event_readiness_score": event_readiness_score,
            "trigger": trigger,
        }

    def score_opportunity(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
        trigger: str = "initial_scout",
    ) -> Dict[str, Any]:

        match_score = self.calculate_match_score(opportunity, business_context)
        readiness_score = self.calculate_readiness_score(opportunity, business_context)
        portfolio_adjusted_readiness = self.calculate_portfolio_adjusted_readiness(opportunity, readiness_score)
        event_readiness_score = self.calculate_event_readiness_score(opportunity, business_context)
        event_readiness_label = self.calculate_event_readiness_label(event_readiness_score)
        roi_data = self.calculate_expected_roi(opportunity)
        why_reason_codes = self.generate_why_reason_codes(opportunity,business_context,match_score)
        data_trust_indicator = self.calculate_data_trust_indicator(opportunity)

        score_history_entry = self.build_score_history_entry(
            match_score=match_score,
            readiness_score=readiness_score,
            event_readiness_score=event_readiness_score,
            trigger=trigger,
        )

        existing_history = opportunity.get("score_history", [])

        updated_history = [
            *existing_history,
            score_history_entry,
        ]

        return {
            "match_score": match_score,
            "readiness_score": readiness_score,
            "portfolio_adjusted_readiness": portfolio_adjusted_readiness,
            "event_readiness_label": event_readiness_label,
            "event_readiness_score": event_readiness_score,
            "expected_roi_mult": roi_data.get("expected_roi_mult"),
            "expected_roi_display": roi_data.get("expected_roi_display"),
            "why_reason_codes": why_reason_codes,
            "data_trust_indicator": data_trust_indicator,
            "score_history": updated_history,
            "last_scored_at": datetime.utcnow(),
        }
    
    async def rescore_opportunity(
        self,
        opportunity: Dict[str, Any],
        business_context: Dict[str, Any],
        trigger: str,
    ) -> Dict[str, Any]:

        scoring_result = self.score_opportunity(
            opportunity=opportunity,
            business_context=business_context,
            trigger=trigger,
        )

        scoring_result["last_scored_at"] = datetime.utcnow()

        return scoring_result


scoring_service = ScoringService()