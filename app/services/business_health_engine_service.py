from typing import Dict, Any, List, Optional

from app.services.benchmark_service import benchmark_service, KPI_TO_BENCHMARK_METRIC
from app.services.kpi_map import KPI_MAP_CONFIG, DEFAULT_KPI_PROFILE
from datetime import datetime, timedelta, timezone
from app.services.quickbooks_financial_service import quickbooks_financial_service
from app.services.signal_engine_service import signal_engine_service
from app.services.lever_engine_service import lever_engine_service
from app.services.behavioral_pattern_service import behavioral_pattern_service
from app.services.cross_business_pattern_service import cross_business_pattern_service
from app.services.business_health_snapshot_service import business_health_snapshot_service
from app.services.financial_signal_service import financial_signal_service


class BusinessHealthEngineService:

    def _build_classifier_params(
        self,
        classifier_output: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not classifier_output:
            return None

        business_type = classifier_output.get("business_type") or classifier_output.get("industry")
        country = classifier_output.get("country") or classifier_output.get("country_code") or "US"
        annual_revenue = classifier_output.get("annual_revenue_dollars") or classifier_output.get("annual_revenue")

        if not business_type or annual_revenue is None:
            return None

        return {
            "business_type": business_type,
            "country": country,
            "annual_revenue_dollars": annual_revenue,
        }

    async def _load_benchmarks(
        self,
        classifier_output: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        params = self._build_classifier_params(classifier_output)
        if params is None:
            return None

        return await benchmark_service.get_or_fetch_benchmarks(
            business_type=params["business_type"],
            country=params["country"],
            annual_revenue_dollars=params["annual_revenue_dollars"],
        )

    def _resolve_kpi_profile(
        self,
        classifier_output: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not classifier_output:
            return DEFAULT_KPI_PROFILE

        business_type = (
            classifier_output.get("business_type")
            or classifier_output.get("industry")
            or ""
        ).lower()

        return KPI_MAP_CONFIG.get(business_type, DEFAULT_KPI_PROFILE)

    def _score_metric(
        self,
        metric_name: str,
        metric_value: Any,
        benchmarks: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        benchmark_metric_key = KPI_TO_BENCHMARK_METRIC.get(metric_name)
        benchmark_metric = None

        if benchmark_metric_key and benchmarks is not None:
            benchmark_metric = benchmarks.get(benchmark_metric_key)

        return benchmark_service.metric_to_score(
            metric_key=benchmark_metric_key or metric_name,
            metric_value=metric_value,
            benchmark_metric=benchmark_metric,
            context=context,
        )

    async def _build_customer_health_metrics(
        self,
        user_id: str,
    ) -> Dict[str, Any]:

        today = datetime.now(timezone.utc).date()
        last_90_days = today - timedelta(days=90)

        revenue_by_customer = []

        try:

            revenue_by_customer = await quickbooks_financial_service.get_revenue_by_customer(
                user_id=user_id,
                start_date=last_90_days,
                end_date=today,
            )

        except Exception:
            revenue_by_customer = []

        revenue_by_customer = revenue_by_customer or []
        total_customers = len(revenue_by_customer)

        repeat_customers = 0

        identified_revenue = 0.0

        total_revenue = 0.0

        for customer in revenue_by_customer or []:

            customer = customer or {}
            amount = float(customer.get("amount", 0) or 0)

            total_revenue += amount

            if customer.get("name") and customer.get("name") != "Unknown":
                identified_revenue += amount

            if amount > 1:
                repeat_customers += 1

        reliability_pct = (
            identified_revenue / total_revenue
            if total_revenue > 0
            else 0
        )

        repeat_rate = None
        repeat_rate_reliable = False

        if reliability_pct > 0.40 and total_customers > 0:

            repeat_rate = repeat_customers / total_customers
            repeat_rate_reliable = True

        churn_risk = None

        if repeat_rate is not None:
            churn_risk = round(1 - repeat_rate, 4)

        customer_health_metrics = {
            "repeat_customer_rate": round(repeat_rate, 4) if repeat_rate is not None else None,
            "repeat_rate_reliable": repeat_rate_reliable,
            "customer_identity_reliability_pct": round(reliability_pct, 4),
            "estimated_churn_risk": churn_risk,
            "identified_customers": total_customers,
            "repeat_customers": repeat_customers,
            "customer_health_data_coverage_prompt": None,
        }

        if not repeat_rate_reliable:

            customer_health_metrics["customer_health_data_coverage_prompt"] = (
                "Connect POS or enable customer identification to unlock Customer Health scoring."
            )

        return customer_health_metrics

    async def _score_category(
        self,
        user_id: str,
        category_name: str,
        category_config: Dict[str, Any],
        metrics: Dict[str, Any],
        benchmarks: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:

        metric_scores = []
        weighted_total = 0
        total_weight = 0
        distress_override = False

        today = datetime.now(timezone.utc).date()
        last_90_days = today - timedelta(days=90)

        revenue_by_customer = []
        overdue_invoices = []
        expense_by_vendor = []
        inventory_breakdown = []
        revenue_by_location = []
        revenue_by_stream = []

        try:
            revenue_by_customer = await quickbooks_financial_service.get_revenue_by_customer(user_id=user_id,start_date=last_90_days,end_date=today)
        except Exception:
            pass

        try:
            overdue_invoices = await quickbooks_financial_service.get_overdue_invoices(user_id=user_id)
        except Exception:
            pass

        try:
            expense_by_vendor = await quickbooks_financial_service.get_expense_by_vendor(user_id=user_id,start_date=last_90_days,end_date=today)
        except Exception:
            pass

        try:
            inventory_breakdown = await quickbooks_financial_service.get_inventory_breakdown(user_id=user_id)
        except Exception:
            pass

        try:
            revenue_by_location = await quickbooks_financial_service.get_revenue_by_location(user_id=user_id,start_date=last_90_days,end_date=today)
        except Exception:
            pass

        try:
            revenue_by_stream = await quickbooks_financial_service.get_revenue_by_stream(user_id=user_id,start_date=last_90_days,end_date=today)
        except Exception:
            pass

        for metric_config in category_config.get("metrics", []):

            metric_name = metric_config.get("metric")
            weight = metric_config.get("weight", 1)

            metric_value = metrics.get(metric_name)

            if metric_value is None:
                continue

            scored_metric = self._score_metric(
                metric_name=metric_name,
                metric_value=metric_value,
                benchmarks=benchmarks,
                context=context,
            )

            scored_metric["weight"] = weight
            scored_metric["actual_value"] = metric_value

            scored_metric["underlying_data"] = {
                "revenue_by_customer": revenue_by_customer[:10],
                "overdue_invoices": overdue_invoices[:10],
                "expense_by_vendor": expense_by_vendor[:10],
                "inventory_breakdown": inventory_breakdown[:10],
                "revenue_by_location": revenue_by_location[:10],
                "revenue_by_stream": revenue_by_stream[:10],
            }

            metric_scores.append(scored_metric)

            score = scored_metric.get("score")

            if isinstance(score, (int, float)):
                weighted_total += score * weight
                total_weight += weight

            if scored_metric.get("distress_override"):
                distress_override = True

        if total_weight == 0:
            return None

        category_score = int(round(weighted_total / total_weight))
        category_label = benchmark_service.score_to_label(category_score)

        if distress_override:
            category_label = "critical"

        return {
            "score": category_score,
            "label": category_label,
            "metrics": metric_scores,
        }

    def _apply_owner_priority_adjustment(
        self,
        category_weights: Dict[str, float],
        classifier_output: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        if not classifier_output:
            return category_weights

        priorities = (
            classifier_output.get("owner_priorities")
            or classifier_output.get("owner_focus")
            or []
        )

        adjusted_weights = dict(category_weights)

        for priority in priorities:
            priority_lower = str(priority).lower()

            if priority_lower == "growth":
                adjusted_weights["growth_health"] = adjusted_weights.get("growth_health", 0) * 1.1

            elif priority_lower == "stability":
                adjusted_weights["financial_health"] = adjusted_weights.get("financial_health", 0) * 1.05
                adjusted_weights["risk_health"] = adjusted_weights.get("risk_health", 0) * 1.05

            elif priority_lower == "profitability":
                adjusted_weights["financial_health"] = adjusted_weights.get("financial_health", 0) * 1.1

        return adjusted_weights

    async def generate_business_health(
        self,
        user_id: str,
        financial_overview: Dict[str, Any],
        classifier_output: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        financial_overview = financial_overview or {}
        classifier_output = classifier_output or {}
        metrics = financial_overview.get("Real Data Metrics", {})
        customer_health_metrics = await self._build_customer_health_metrics(
            user_id=user_id,
        )

        metrics.update(customer_health_metrics)
        signal_metrics = {
            "runway_months": financial_overview.get(
                "cashflow",
                {},
            ).get(
                "runway_months",
            ),
            "gross_margin_pct": financial_overview.get(
                "kpis",
                {},
            ).get(
                "gross_margin_pct",
            ),
        }
        financial_signals = await financial_signal_service.build_financial_signals(
            user_id=user_id,
            metrics=signal_metrics,
            classifier_output=classifier_output or {},
        )
        signal_surfaces = signal_engine_service.evaluate_signals(
            metrics=metrics,
            classifier_output=classifier_output or {},
        )
        signal_surfaces = lever_engine_service.attach_levers(
            signal_surfaces=signal_surfaces,
            classifier_output=classifier_output or {},
        )
        behavioral_patterns = await behavioral_pattern_service.compute_owner_patterns(
            user_id=user_id,
        )
        cross_business_patterns = await cross_business_pattern_service.build_similar_business_patterns(
            classifier_output=classifier_output or {},
        )
        benchmarks = await self._load_benchmarks(classifier_output)

        context = classifier_output or {}

        kpi_profile = self._resolve_kpi_profile(classifier_output)

        category_results = {}

        for category_name, category_config in kpi_profile.get("categories", {}).items():

            category_results[category_name] =await self._score_category(
                user_id=user_id,
                category_name=category_name,
                category_config=category_config,
                metrics=metrics,
                benchmarks=benchmarks,
                context=context,
            )

        category_weights = self._apply_owner_priority_adjustment(
            kpi_profile.get("category_weights", {}),
            classifier_output,
        )

        overall_weighted_total = 0
        overall_total_weight = 0
        overall_critical = False

        for category_name, category_result in category_results.items():

            if category_result is None:
                continue

            score = category_result.get("score")

            if not isinstance(score, (int, float)):
                continue

            weight = category_weights.get(category_name, 1)

            overall_weighted_total += score * weight
            overall_total_weight += weight

            if category_result.get("label") == "critical":
                overall_critical = True

        overall = None

        if overall_total_weight > 0:

            overall_score = int(round(overall_weighted_total / overall_total_weight))

            overall_label = benchmark_service.score_to_label(overall_score)

            if overall_critical:
                overall_label = "critical"

            overall = {
                "score": overall_score,
                "label": overall_label,
            }

        final_payload = {
            "overall": overall,
            "financial_signals": financial_signals,
            "similar_business_patterns": cross_business_patterns.get("similar_business_patterns", []),
            "behavioral_patterns": behavioral_patterns,
            "active_health_alerts": signal_surfaces.get("active_health_alerts", []),
            "priority_watch_areas": signal_surfaces.get("priority_watch_areas", []),
            "score_drivers": signal_surfaces.get("score_drivers", []),
            "financial_health": category_results.get("financial_health"),
            "operational_health": category_results.get("operational_health"),
            "risk_health": category_results.get("risk_health"),
            "growth_health": category_results.get("growth_health"),
        }

        await business_health_snapshot_service.create_snapshot(
            user_id=user_id,
            business_health_payload=final_payload,
            classifier_output=classifier_output,
        )

        return final_payload


business_health_engine_service = BusinessHealthEngineService()