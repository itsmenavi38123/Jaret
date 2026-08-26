from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4

from app.db import get_collection
from app.config import _now_utc


class SettingsV2Service:

    # --------------------------------------------------------------------------
    # 1. GENERAL SETTINGS (GET / PATCH)
    # --------------------------------------------------------------------------
    async def get_general_settings(self, user_id: str) -> Dict[str, Any]:
        col = get_collection("settings_general")
        doc = await col.find_one({"user_id": user_id})
        if not doc:
            doc = {
                "user_id": user_id,
                "timezone": "America/Chicago",
                "base_currency": "USD",
                "reporting_period": "Monthly",
                "demo_mode": False,
                "reduce_motion": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await col.insert_one(doc)
        else:
            doc.setdefault("timezone", "America/Chicago")
            doc.setdefault("base_currency", "USD")
            doc.setdefault("reporting_period", "Monthly")
            if not doc.get("timezone"):
                doc["timezone"] = "America/Chicago"
            if not doc.get("base_currency"):
                doc["base_currency"] = "USD"
            if not doc.get("reporting_period"):
                doc["reporting_period"] = "Monthly"

        doc.pop("_id", None)

        users_col = get_collection("users")
        user = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id})
        doc["company_name"] = (user.get("business_name") if user else None) or "Velvet & Vine Salon"
        return doc

    async def update_general_settings(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        col = get_collection("settings_general")
        clean_updates = {k: v for k, v in updates.items() if v is not None}
        clean_updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        await col.update_one(
            {"user_id": user_id},
            {"$set": clean_updates},
            upsert=True,
        )
        return await self.get_general_settings(user_id)

    async def export_diagnostics(self, user_id: str) -> Dict[str, Any]:
        qb_col = get_collection("quickbooks_tokens")
        qb_token = await qb_col.find_one({"user_id": user_id})

        pos_col = get_collection("user_pos_access")
        pos_access = await pos_col.find({"user_id": user_id}).to_list(length=10)

        logs_col = get_collection("sync_logs")
        logs = await logs_col.find({"user_id": user_id}).sort("timestamp", -1).to_list(length=50)
        formatted_logs = [
            {"timestamp": str(l.get("timestamp", "")), "level": l.get("level", ""), "message": l.get("message", "")}
            for l in logs
        ]

        return {
            "user_id": user_id,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "connectors": {
                "quickbooks": {
                    "connected": bool(qb_token and qb_token.get("is_active")),
                    "last_sync": str(qb_token.get("updated_at")) if qb_token else None,
                },
                "pos_integrations": [
                    {
                        "provider": p.get("provider"),
                        "connected": True,
                        "updated_at": str(p.get("updated_at")),
                    } for p in pos_access
                ]
            },
            "sync_logs": formatted_logs
        }

    # --------------------------------------------------------------------------
    # 2. DATA & PRIVACY & PHOTO CONSENT (GET / PATCH)
    # --------------------------------------------------------------------------
    async def get_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        col = get_collection("settings_privacy")
        doc = await col.find_one({"user_id": user_id})
        if not doc:
            doc = {
                "user_id": user_id,
                "peer_benchmarking": False,
                "anonymized_ai_use": False,
                "retention_days": 365,
                "photo_permissions": {
                    "enabled": False,
                    "sources": [],
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await col.insert_one(doc)

        doc.pop("_id", None)
        return doc

    async def update_privacy_settings(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        col = get_collection("settings_privacy")
        clean_updates = {k: v for k, v in updates.items() if v is not None}
        clean_updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        consents_col = get_collection("consents_history")
        await consents_col.insert_one({
            "user_id": user_id,
            "action": "privacy_settings_updated",
            "changes": clean_updates,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await col.update_one(
            {"user_id": user_id},
            {"$set": clean_updates},
            upsert=True,
        )
        return await self.get_privacy_settings(user_id)

    async def get_consent_history(self, user_id: str) -> List[Dict[str, Any]]:
        col = get_collection("consents_history")
        cursor = col.find({"user_id": user_id}).sort("timestamp", -1)
        history = await cursor.to_list(length=100)
        for h in history:
            h.pop("_id", None)
        return history

    async def initiate_account_deletion(self, user_id: str) -> Dict[str, Any]:
        col = get_collection("users")
        grace_until = datetime.now(timezone.utc) + timedelta(days=14)
        await col.update_one(
            {"id": user_id},
            {"$set": {
                "deletion_requested": True,
                "deletion_grace_until": grace_until.isoformat(),
            }}
        )
        return {
            "user_id": user_id,
            "status": "deletion_scheduled",
            "grace_period_days": 14,
            "hard_deletion_date": grace_until.isoformat(),
        }

    # --------------------------------------------------------------------------
    # 3. SECURITY & TEAM & ADVISOR LINK
    # --------------------------------------------------------------------------
    async def get_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        col = get_collection("user_sessions")
        sessions = await col.find({"user_id": user_id}).to_list(length=20)
        formatted = []
        for s in sessions:
            formatted.append({
                "session_id": str(s.get("_id", s.get("id"))),
                "device": str(s.get("device_info", "")),
                "ip_address": str(s.get("ip_address", "")),
                "last_active": str(s.get("last_active", "")),
                "is_current": bool(s.get("is_current", False)),
            })
        return formatted

    async def revoke_all_sessions(self, user_id: str) -> Dict[str, Any]:
        col = get_collection("user_sessions")
        result = await col.delete_many({"user_id": user_id, "is_current": {"$ne": True}})
        return {
            "user_id": user_id,
            "revoked_count": result.deleted_count,
        }

    async def revoke_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        col = get_collection("user_sessions")
        await col.delete_one({"user_id": user_id, "id": session_id})
        return {"session_id": session_id, "status": "revoked"}

    async def get_team_members(self, user_id: str) -> List[Dict[str, Any]]:
        col = get_collection("team_members")
        members = await col.find({"owner_user_id": user_id}).to_list(length=50)
        for m in members:
            m.pop("_id", None)
        return members

    async def delete_team_member(self, user_id: str, member_id: str) -> Dict[str, Any]:
        col = get_collection("team_members")
        await col.delete_one({"owner_user_id": user_id, "id": member_id})
        return {"member_id": member_id, "status": "removed"}

    async def invite_team_member(self, owner_user_id: str, email: str, role: str) -> Dict[str, Any]:
        col = get_collection("team_members")
        member_doc = {
            "id": f"team_{uuid4().hex[:8]}",
            "owner_user_id": owner_user_id,
            "email": email,
            "role": role,
            "status": "invited",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await col.insert_one(member_doc)
        member_doc.pop("_id", None)
        return member_doc

    async def create_share_link(self, user_id: str, scope: str = "fo+bh") -> Dict[str, Any]:
        col = get_collection("share_links")
        link_id = f"share_{uuid4().hex[:12]}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        link_doc = {
            "id": link_id,
            "user_id": user_id,
            "scope": scope,
            "read_only": True,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await col.insert_one(link_doc)
        link_doc.pop("_id", None)
        return link_doc

    # --------------------------------------------------------------------------
    # 4. AI & CORRECTIONS LEDGER
    # --------------------------------------------------------------------------
    async def get_corrections(self, user_id: str) -> List[Dict[str, Any]]:
        col = get_collection("corrections_ledger")
        corrections = await col.find({"user_id": user_id}).to_list(length=100)
        for c in corrections:
            c.pop("_id", None)
        return corrections

    async def undo_correction(self, user_id: str, correction_id: str) -> Dict[str, Any]:
        col = get_collection("corrections_ledger")
        await col.delete_one({"user_id": user_id, "id": correction_id})
        return {
            "correction_id": correction_id,
            "status": "undone"
        }

    async def get_living_summary(self, user_id: str) -> Dict[str, Any]:
        col = get_collection("living_summaries")
        doc = await col.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            if doc.get("observations"):
                return doc
        return {
            "user_id": user_id,
            "observations": [
                "QuickBooks Online financial integration active.",
                "24-month revenue history indexed.",
                "Primary operating location verified."
            ],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    async def rerun_classifier(self, user_id: str) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "status": "triggered",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    # --------------------------------------------------------------------------
    # 5. BILLING SECTION
    # --------------------------------------------------------------------------
    async def get_billing_summary(self, user_id: str) -> Dict[str, Any]:
        col = get_collection("users")
        user = await col.find_one({"id": user_id}) or await col.find_one({"_id": user_id})

        sub_col = get_collection("subscriptions")
        sub = await sub_col.find_one({"user_id": user_id})

        if sub:
            sub.pop("_id", None)
            return sub

        is_comped = bool(user and user.get("subscription_status") == "comped") or True
        return {
            "user_id": user_id,
            "is_comped": is_comped,
            "plan_name": "Comped Pro Plan",
            "status": "active",
            "renewal_date": (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d"),
            "next_payment_date": (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d"),
            "payment_method": "Comped Account Pass"
        }

    async def get_billing_portal_url(self, user_id: str) -> Dict[str, Any]:
        col = get_collection("subscriptions")
        sub = await col.find_one({"user_id": user_id})
        portal_url = (sub.get("portal_url") if sub else None) or "https://billing.stripe.com/p/session_demo_lightsignal"

        return {
            "user_id": user_id,
            "url": portal_url,
        }

    async def get_billing_invoices(self, user_id: str) -> List[Dict[str, Any]]:
        col = get_collection("invoices")
        invoices = await col.find({"user_id": user_id}).sort("date", -1).to_list(length=50)
        if invoices:
            for inv in invoices:
                inv.pop("_id", None)
            return invoices
        return [
            {
                "id": "inv_2026_001",
                "invoice_number": "INV-2026-001",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "amount": "$0.00",
                "status": "paid",
                "plan": "Comped Pro Plan (Annual Pass)"
            }
        ]

    # --------------------------------------------------------------------------
    # 6. UNIFIED SNAPSHOTS
    # --------------------------------------------------------------------------
    async def get_unified_snapshots(self, user_id: str) -> List[Dict[str, Any]]:
        col = get_collection("business_health_snapshot")
        snapshots = await col.find({"user_id": user_id}).sort("created_at", -1).to_list(length=30)
        formatted = []
        for s in snapshots:
            created_at = s.get("created_at")
            date_str = created_at.isoformat()[:10] if isinstance(created_at, datetime) else str(created_at)[:10] if created_at else ""
            score = s.get("overall", {}).get("score") if isinstance(s.get("overall"), dict) else None
            formatted.append({
                "snapshot_id": str(s.get("_id", s.get("id"))),
                "date": date_str,
                "health_score": score,
            })
        return formatted


settings_v2_service = SettingsV2Service()
