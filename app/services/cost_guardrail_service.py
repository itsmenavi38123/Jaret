# backend/app/services/cost_guardrail_service.py
from datetime import datetime
from typing import Tuple, Dict, Any
from app.db import get_collection
from app.services.admin_notification_service import AdminNotificationService

admin_notif_service = AdminNotificationService()

class CostGuardrailService:
    def __init__(self):
        self.usage_col = get_collection("account_usage_daily")
        self.settings_col = get_collection("settings")

    async def _get_today_date_str(self) -> str:
        # Return UTC date string format YYYY-MM-DD
        return datetime.utcnow().strftime("%Y-%m-%d")

    async def check_and_reserve(self, account_id: str, surface: str) -> Tuple[bool, str]:
        today_str = await self._get_today_date_str()
        
        # Load configuration (with hardcoded placeholders if config missing)
        config = await self.settings_col.find_one({"_id": "site_config"}) or {}
        
        hard_ceiling = config.get("account_daily_hard_ceiling", 1000)  # cents ($10.00)
        soft_alert = config.get("account_daily_soft_alert", 600)      # cents ($6.00)
        
        cap_manual_refresh = config.get("cap_manual_refresh", 3)
        cap_scenario_runs = config.get("cap_scenario_runs", 15)
        cap_dia_uploads = config.get("cap_dia_uploads", 50)
        
        cost_estimates = config.get("cost_estimates", {
            "scout_ondemand": 15,
            "dashboard_ask": 20,
            "drawer_ask": 10,
            "manual_refresh": 150,
            "scenario_run": 60,
            "dia_upload": 20
        })

        est_cost = cost_estimates.get(surface, 0)

        # Check or create the daily counter row
        row = await self.usage_col.find_one({"account_id": account_id, "date": today_str})
        if not row:
            row = {
                "account_id": account_id,
                "date": today_str,
                "cost_cents_total": 0,
                "manual_refresh_count": 0,
                "scenario_run_count": 0,
                "dia_upload_count": 0,
                "soft_alert_fired": False,
                "last_call_at": datetime.utcnow()
            }
            await self.usage_col.insert_one(row)

        # 1. Per-surface cap validations
        if surface == "manual_refresh" and row.get("manual_refresh_count", 0) >= cap_manual_refresh:
            return False, "surface_cap"
        if surface == "scenario_run" and row.get("scenario_run_count", 0) >= cap_scenario_runs:
            return False, "surface_cap"
        if surface == "dia_upload" and row.get("dia_upload_count", 0) >= cap_dia_uploads:
            return False, "surface_cap"

        # 2. Hard ceiling validation
        if row.get("cost_cents_total", 0) + est_cost > hard_ceiling:
            return False, "account_ceiling"

        # 3. Reserve spend and increment counts
        updates: Dict[str, Any] = {
            "cost_cents_total": est_cost,
        }
        if surface == "manual_refresh":
            updates["manual_refresh_count"] = 1
        elif surface == "scenario_run":
            updates["scenario_run_count"] = 1
        elif surface == "dia_upload":
            updates["dia_upload_count"] = 1

        new_total = row.get("cost_cents_total", 0) + est_cost
        
        # Soft alert triggers (once per day when crossing the line)
        soft_alert_fired_updated = row.get("soft_alert_fired", False)
        if new_total >= soft_alert and not soft_alert_fired_updated:
            await admin_notif_service.create_notification(
                title="Usage Soft Alert Limit Reached",
                message=f"Account {account_id} reached daily estimated usage soft limit: ${new_total / 100:.2f}",
                notification_type="usage_soft_alert"
            )
            updates["soft_alert_fired"] = True

        await self.usage_col.update_one(
            {"account_id": account_id, "date": today_str},
            {
                "$inc": {k: v for k, v in updates.items() if isinstance(v, (int, float)) and not isinstance(v, bool)},
                "$set": {
                    "last_call_at": datetime.utcnow(),
                    **{k: v for k, v in updates.items() if not isinstance(v, (int, float)) or isinstance(v, bool)}
                }
            }
        )

        return True, ""

    async def refund_reserve(self, account_id: str, surface: str):
        today_str = await self._get_today_date_str()
        
        config = await self.settings_col.find_one({"_id": "site_config"}) or {}
        cost_estimates = config.get("cost_estimates", {
            "scout_ondemand": 15,
            "dashboard_ask": 20,
            "drawer_ask": 10,
            "manual_refresh": 150,
            "scenario_run": 60,
            "dia_upload": 20
        })
        est_cost = cost_estimates.get(surface, 0)

        decrements: Dict[str, Any] = {
            "cost_cents_total": -est_cost
        }
        if surface == "manual_refresh":
            decrements["manual_refresh_count"] = -1
        elif surface == "scenario_run":
            decrements["scenario_run_count"] = -1
        elif surface == "dia_upload":
            decrements["dia_upload_count"] = -1

        await self.usage_col.update_one(
            {"account_id": account_id, "date": today_str},
            {"$inc": decrements}
        )

cost_guardrail_service = CostGuardrailService()
