# backend/app/demo_data/__init__.py
"""
Aggregated Spec-Compliant Demo Payloads for All 7 Demo Accounts.
Maps each login_label to its full, authentic payload structure.
"""
from typing import Any, Dict, Optional

from app.demo_data.demo_restaurant import TONYS_BROOKLYN_PIZZA_PAYLOADS
from app.demo_data.demo_retail import MAIN_ST_GOODS_PAYLOADS
from app.demo_data.demo_service import IRONWOOD_PLUMBING_PAYLOADS
from app.demo_data.demo_salon import VELVET_VINE_SALON_PAYLOADS
from app.demo_data.demo_multi import DRIFTWOOD_COFFEE_PAYLOADS
from app.demo_data.demo_ecomm import LAKESHORE_CANDLE_PAYLOADS
from app.demo_data.demo_fitness import SOUTHPOINT_FITNESS_PAYLOADS

DEMO_ACCOUNTS_MAP: Dict[str, Dict[str, Any]] = {
    "demo-restaurant": TONYS_BROOKLYN_PIZZA_PAYLOADS,
    "demo-retail": MAIN_ST_GOODS_PAYLOADS,
    "demo-service": IRONWOOD_PLUMBING_PAYLOADS,
    "demo-salon": VELVET_VINE_SALON_PAYLOADS,
    "demo-multi": DRIFTWOOD_COFFEE_PAYLOADS,
    "demo-ecomm": LAKESHORE_CANDLE_PAYLOADS,
    "demo-fitness": SOUTHPOINT_FITNESS_PAYLOADS,
}


def get_demo_payload(login_label: str) -> Optional[Dict[str, Any]]:
    """Retrieve full spec-compliant payload by demo login label."""
    return DEMO_ACCOUNTS_MAP.get(login_label)


def get_demo_payload_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve payload by demo account email."""
    for label, payload in DEMO_ACCOUNTS_MAP.items():
        if payload.get("account", {}).get("email") == email:
            return payload
    return None
