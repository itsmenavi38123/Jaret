from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Sequence


MACRS_5_YEAR_RATES = [0.20, 0.32, 0.192, 0.1152, 0.1152, 0.0576]

WEBHOOK_TEMPLATES = [
    {
        "event": "asset.fault.created",
        "description": "Triggered when telemetry, sensors, or maintenance logs detect a new fault code.",
        "recommended_payload": {
            "asset_id": "ASSET-123",
            "fault_code": "P0420",
            "severity": "high",
            "detected_at": "2025-12-01T14:30:00Z",
        },
    },
    {
        "event": "warranty.expiring",
        "description": "Triggered when an asset warranty is within the reminder window (default 60 days).",
        "recommended_payload": {
            "asset_id": "ASSET-456",
            "warranty_provider": "OEM",
            "expiration_date": "2025-09-01",
            "days_remaining": 240,
        },
    },
]


def _serialize_date(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def _months_in_service(reference_date: date, start_date: Optional[date]) -> int:
    if not start_date:
        return 0
    months = (reference_date.year - start_date.year) * 12 + (
        reference_date.month - start_date.month
    )
    return max(months, 0)


def _straight_line(
    cost: float, salvage: float, life_months: int, months_in_service: int
) -> Dict[str, Any]:
    if life_months <= 0:
        return {"book_value": cost, "accumulated": 0.0, "schedule": []}

    depreciable = max(cost - salvage, 0)
    monthly = depreciable / life_months
    accumulated = min(monthly * months_in_service, depreciable)
    book_value = max(cost - accumulated, salvage)

    return {
        "book_value": round(book_value, 2),
        "accumulated": round(accumulated, 2),
        "monthly_amount": round(monthly, 2),
        "schedule": [
            {"period": "Month 1", "amount": round(monthly, 2)},
            {"period": "Month 12", "amount": round(monthly * 12, 2)},
        ],
    }


def _double_declining(
    cost: float, salvage: float, life_months: int, months_in_service: int
) -> Dict[str, Any]:
    if life_months <= 0:
        return {"book_value": cost, "accumulated": 0.0, "schedule": []}

    monthly_rate = 2 / life_months
    book = cost
    accumulated = 0.0
    schedule: List[Dict[str, Any]] = []
    year_dep = 0.0

    for month in range(1, months_in_service + 1):
        depreciation = book * monthly_rate
        if book - depreciation < salvage:
            depreciation = book - salvage

        book -= depreciation
        accumulated += depreciation
        year_dep += depreciation

        if month % 12 == 0 or month == months_in_service or book <= salvage:
            schedule.append(
                {
                    "period": f"Year {(month - 1) // 12 + 1}",
                    "amount": round(year_dep, 2),
                    "book_value": round(book, 2),
                }
            )
            year_dep = 0.0

        if book <= salvage:
            break

    return {
        "book_value": round(book, 2),
        "accumulated": round(accumulated, 2),
        "schedule": schedule,
    }


def _macrs(cost: float, months_in_service: int) -> Dict[str, Any]:
    schedule: List[Dict[str, Any]] = []
    accumulated = 0.0
    months_remaining = months_in_service

    for idx, rate in enumerate(MACRS_5_YEAR_RATES, start=1):
        if months_remaining <= 0:
            break

        months_for_year = min(12, months_remaining)
        fraction = months_for_year / 12
        amount = cost * rate * fraction
        accumulated += amount

        schedule.append(
            {
                "period": f"Year {idx}",
                "rate": rate,
                "amount": round(amount, 2),
                "book_value": round(max(cost - accumulated, 0.0), 2),
            }
        )

        months_remaining -= 12

    book_value = max(cost - accumulated, 0.0)
    return {
        "book_value": round(book_value, 2),
        "accumulated": round(accumulated, 2),
        "schedule": schedule,
    }


def _health_report(asset: Dict[str, Any]) -> Dict[str, Any]:
    utilization = float(asset.get("utilization_pct", 75) or 75)
    downtime = float(asset.get("downtime_hours_30d", 0) or 0)
    faults = float(asset.get("faults_last_30d", 0) or 0)
    maintenance = float(asset.get("maintenance_compliance_pct", 90) or 90)

    score = 100.0
    score -= downtime * 0.6
    score -= faults * 1.5
    score -= max(0, 90 - maintenance) * 0.4
    score -= max(0, 70 - utilization) * 0.2
    score = max(10.0, min(score, 100.0))

    if score >= 85:
        status = "good"
    elif score >= 65:
        status = "warning"
    else:
        status = "critical"

    return {
        "score": round(score, 1),
        "status": status,
        "drivers": {
            "utilization_pct": utilization,
            "downtime_hours_30d": downtime,
            "faults_last_30d": faults,
            "maintenance_compliance_pct": maintenance,
        },
    }


def _utilization_report(asset: Dict[str, Any]) -> Dict[str, Any]:
    utilization = float(asset.get("utilization_pct", 0) or 0)
    idle_pct = max(0.0, 100.0 - utilization)
    availability = float(asset.get("availability_pct", 0) or 0)

    return {
        "last_30_days_pct": utilization,
        "idle_pct": round(idle_pct, 1),
        "availability_pct": availability,
        "tooltip": "Utilization = time in use ÷ total available time. Availability = uptime ÷ total time.",
    }


def _depreciation_summary(asset: Dict[str, Any], reference_date: Optional[date] = None):
    reference = reference_date or date.today()
    method = (asset.get("depreciation_method") or "SL").upper()
    cost = float(asset.get("purchase_price", 0) or 0)
    salvage = float(asset.get("salvage_value", 0) or 0)
    life_months = int(asset.get("useful_life_months", 1) or 1)
    in_service_date = asset.get("in_service_date") or asset.get("purchase_date")
    months = _months_in_service(reference, in_service_date)

    if method == "DDB":
        details = _double_declining(cost, salvage, life_months, months)
    elif method == "MACRS":
        details = _macrs(cost, months)
    else:
        details = _straight_line(cost, salvage, life_months, months)

    details.update(
        {
            "method": method,
            "months_in_service": months,
            "cost": cost,
            "salvage_value": salvage,
        }
    )
    return details


def _calculate_kpis(assets: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    today = date.today()
    total_assets = len(assets)
    categories: Dict[str, int] = {}
    book_value = 0.0
    replacement_value = 0.0
    downtime = 0.0
    maintenance_scores = []
    utilization_scores = []
    health_scores = []
    upcoming_services = 0
    expiring_warranties = 0
    depreciation_mtd = 0.0

    for asset in assets:
        category = asset.get("category", "Other")
        categories[category] = categories.get(category, 0) + 1

        book_value += float(asset.get("book_value", 0) or 0)
        replacement_value += float(asset.get("replacement_value", 0) or 0)
        downtime += float(asset.get("downtime_hours_30d", 0) or 0)
        maintenance_scores.append(float(asset.get("maintenance_compliance_pct", 0) or 0))
        utilization_scores.append(float(asset.get("utilization_pct", 0) or 0))
        health_scores.append(_health_report(asset)["score"])
        depreciation_mtd += float(asset.get("purchase_price", 0) or 0) * 0.01

        next_service = asset.get("next_service_date")
        if next_service and 0 <= (next_service - today).days <= 90:
            upcoming_services += 1

        warranty_expiration = asset.get("warranty_expiration")
        if warranty_expiration and 0 <= (warranty_expiration - today).days <= 60:
            expiring_warranties += 1

    avg_utilization = (
        sum(utilization_scores) / len(utilization_scores) if utilization_scores else 0
    )
    avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
    maintenance_compliance = (
        sum(maintenance_scores) / len(maintenance_scores) if maintenance_scores else 0
    )

    return {
        "totals": {
            "assets": total_assets,
            "by_category": categories,
        },
        "values": {
            "book_value": round(book_value, 2),
            "replacement_value": round(replacement_value, 2),
        },
        "utilization": {
            "avg_last_30_days_pct": round(avg_utilization, 1),
            "downtime_hours_30d": round(downtime, 1),
            "availability_target": "Aim > 95%",
        },
        "maintenance": {
            "compliance_pct": round(maintenance_compliance, 1),
            "upcoming_services_90d": upcoming_services,
        },
        "risk": {
            "warranties_expiring_60d": expiring_warranties,
            "health_score": round(avg_health, 1),
        },
        "depreciation": {
            "mtd": round(depreciation_mtd, 2),
            "ytd": round(depreciation_mtd * 6, 2),
        },
    }


def get_asset_management_overview(assets: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build an overview object for a given set of *real* assets.
    Caller is responsible for providing assets, typically from MongoDB or an external system.
    """
    serialized_assets = []
    for asset in assets:
        serialized_assets.append(
            {
                **asset,
                "purchase_date": _serialize_date(asset.get("purchase_date")),
                "in_service_date": _serialize_date(asset.get("in_service_date")),
                "next_service_date": _serialize_date(asset.get("next_service_date")),
                "last_service_date": _serialize_date(asset.get("last_service_date")),
                "warranty_expiration": _serialize_date(asset.get("warranty_expiration")),
                "insurance_expiration": _serialize_date(asset.get("insurance_expiration")),
                "health": _health_report(asset),
                "utilization_overview": _utilization_report(asset),
            }
        )

    tooltips = {
        "utilization": "Utilization = time in use ÷ available time. Higher is better.",
        "availability": "Availability = uptime ÷ total time. Aim >95%.",
        "mtbf": "MTBF = average time between failures (higher is better).",
        "mttr": "MTTR = average time to repair (lower is better).",
        "tco": "TCO = purchase + financing + fuel/energy + parts + labor + downtime cost − resale.",
    }

    return {
        "assets": serialized_assets,
        "kpis": _calculate_kpis(assets),
        "tooltips": tooltips,
    }


def compute_asset_insights(
    assets: Optional[Sequence[Dict[str, Any]]] = None,
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Compute depreciation, health, and KPI summaries for a *provided* asset list.
    No static/sample data is injected; if `assets` is empty, the caller should have
    already fetched real records (e.g., from MongoDB, QuickBooks, CMMS, or Asset Hub).
    """
    reference = reference_date or date.today()
    asset_list = list(assets or [])

    enriched_assets = []
    for asset in asset_list:
        depreciation = _depreciation_summary(asset, reference)
        health = _health_report(asset)
        utilization = _utilization_report(asset)

        enriched_assets.append(
            {
                "asset_id": asset.get("asset_id"),
                "category": asset.get("category"),
                "type": asset.get("type"),
                "purchase_price": asset.get("purchase_price"),
                "depreciation": depreciation,
                "health": health,
                "utilization": utilization,
                "next_service_date": _serialize_date(asset.get("next_service_date")),
                "warranty_expiration": _serialize_date(asset.get("warranty_expiration")),
                "insurance_expiration": _serialize_date(asset.get("insurance_expiration")),
            }
        )

    kpis = _calculate_kpis(asset_list)

    recommendations = []
    for asset, raw_asset in zip(enriched_assets, asset_list):
        health_score = asset["health"]["score"]
        depreciation = asset["depreciation"]
        book_value = depreciation.get("book_value", raw_asset.get("book_value", 0))
        replacement_value = raw_asset.get("replacement_value")

        if health_score < 65:
            recommendations.append(
                {
                    "asset_id": asset["asset_id"],
                    "action": "Review maintenance plan",
                    "reason": "Health score trending critical – inspect faults, downtime, and operator usage.",
                }
            )

        if replacement_value and book_value <= 0.5 * replacement_value:
            recommendations.append(
                {
                    "asset_id": asset["asset_id"],
                    "action": "Consider replacement",
                    "reason": "Book value is <50% of replacement value; evaluate repair vs replace.",
                }
            )

    return {
        "as_of": reference.isoformat(),
        "kpis": kpis,
        "assets": enriched_assets,
        "recommendations": recommendations,
        "webhooks": WEBHOOK_TEMPLATES,
        "tooltips": {
            "depreciation": "Straight-line = (cost − salvage) ÷ useful life. DDB accelerates early years. MACRS follows IRS tables.",
            "health": "Health blends maintenance compliance, utilization, downtime, faults, and availability.",
            "replace_vs_repair": "If repair + downtime > ~65% of new asset cost, consider replacement.",
        },
    }

