# backend/app/services/scheduler_budget_service.py
from datetime import datetime, timedelta
from typing import Tuple
from app.db import get_collection

async def check_user_activity_and_connection(user_id: str) -> Tuple[bool, str]:
    """
    Checks if a user has active connected data OR recent activity in the last 14 days.
    Returns (should_process, reason)
    """
    users = get_collection("users")
    quickbooks_tokens = get_collection("quickbooks_tokens")
    xero_tokens = get_collection("xero_tokens")
    business_profiles = get_collection("business_profiles")
    documents = get_collection("documents")

    user = await users.find_one({"_id": user_id})
    if not user:
        user = await users.find_one({"_id": str(user_id)})
    if not user:
        return False, "User record not found"

    if user.get("is_deactivated"):
        return False, "User account is deactivated"

    # 1. Connected Data Check
    qb_connected = await quickbooks_tokens.find_one({"user_id": user_id, "is_active": True})
    xero_connected = await xero_tokens.find_one({"user_id": user_id, "is_active": True})
    doc_count = await documents.count_documents({"user_id": user_id})
    
    profile = await business_profiles.find_one({"user_id": user_id})
    has_integrations = False
    if profile:
        onboarding = profile.get("onboarding_data", {})
        connected_list = onboarding.get("connected_integrations", []) or onboarding.get("integrations", [])
        if connected_list:
            has_integrations = True

    has_connected_data = bool(qb_connected or xero_connected or doc_count > 0 or has_integrations)

    # 2. Activity in last 14 days Check
    cutoff_14d = datetime.utcnow() - timedelta(days=14)
    last_activity = (
        user.get("last_login") or 
        user.get("last_activity_at") or 
        user.get("updated_at") or 
        user.get("created_at")
    )
    
    has_recent_activity = False
    if last_activity:
        if isinstance(last_activity, str):
            try:
                last_activity = datetime.fromisoformat(last_activity.replace("Z", ""))
            except Exception:
                last_activity = None
        if isinstance(last_activity, datetime) and last_activity >= cutoff_14d:
            has_recent_activity = True

    if not has_connected_data and not has_recent_activity:
        print(f"[Nightly Scheduler] Skipped user {user_id}: no connected data and no activity in last 14 days.")
        return False, "No connected data & inactive for 14+ days"

    return True, "Eligible"
