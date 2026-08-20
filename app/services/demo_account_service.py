# backend/app/services/demo_account_service.py
import json
import os
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from app.db import get_collection
from app.routes.auth.auth import hash_password
from app.services.demo_generator_service import demo_generator_service

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Demo Accounts")

DEMO_ACCOUNTS_MAP = [
    {
        "biz_id": "demo-restaurant",
        "name": "Tony's Brooklyn Pizza",
        "email": "demo-restaurant@lightsignal.app",
        "default_pass": "PizzaDemo2026!",
        "vertical": "restaurant"
    },
    {
        "biz_id": "demo-retail",
        "name": "Main St Goods",
        "email": "demo-retail@lightsignal.app",
        "default_pass": "RetailDemo2026!",
        "vertical": "retail"
    },
    {
        "biz_id": "demo-service",
        "name": "Ironwood Plumbing & Heating",
        "email": "demo-service@lightsignal.app",
        "default_pass": "ServiceDemo2026!",
        "vertical": "trades"
    },
    {
        "biz_id": "demo-salon",
        "name": "Velvet & Vine Salon",
        "email": "demo-salon@lightsignal.app",
        "default_pass": "SalonDemo2026!",
        "vertical": "health_wellness"
    },
    {
        "biz_id": "demo-multi",
        "name": "Driftwood Coffee Roasters",
        "email": "demo-multi@lightsignal.app",
        "default_pass": "CoffeeDemo2026!",
        "vertical": "multi_location"
    },
    {
        "biz_id": "demo-ecomm",
        "name": "Lakeshore Candle Co.",
        "email": "demo-ecomm@lightsignal.app",
        "default_pass": "EcommDemo2026!",
        "vertical": "e-commerce"
    },
    {
        "biz_id": "demo-fitness",
        "name": "Southpoint Fitness Studio",
        "email": "demo-fitness@lightsignal.app",
        "default_pass": "FitnessDemo2026!",
        "vertical": "fitness"
    }
]

class DemoAccountService:
    async def provision_all_demo_accounts(self, backfill_months: int = 24) -> List[Dict[str, Any]]:
        results = []
        epoch_date = date(2026, 7, 1)

        users_col = get_collection("users")
        profiles_col = get_collection("business_profiles")

        configs = demo_generator_service.load_configs()

        for demo in DEMO_ACCOUNTS_MAP:
            biz_id = demo["biz_id"]
            email = demo["email"]
            name = demo["name"]

            existing_user = await users_col.find_one({"email": email})
            if not existing_user:
                user_doc = {
                    "_id": f"usr_{biz_id}",
                    "id": f"usr_{biz_id}",
                    "email": email,
                    "full_name": name,
                    "business_name": name,
                    "password_hash": hash_password(demo["default_pass"]),
                    "hashed_password": hash_password(demo["default_pass"]),
                    "plain_demo_pass": demo["default_pass"],
                    "is_demo": True,
                    "is_verified": True,
                    "is_paused": False,
                    "signup_source": "demo",
                    "created_at": datetime.utcnow(),
                    "subscription_status": "comped"
                }
                await users_col.insert_one(user_doc)
                user_id = user_doc["id"]
            else:
                user_id = existing_user.get("id", str(existing_user.get("_id")))
                update_fields = {
                    "is_demo": True,
                    "is_verified": True,
                    "is_paused": False,
                    "subscription_status": "comped"
                }
                # Only set password fields if not already present
                if "password_hash" not in existing_user:
                    update_fields["password_hash"] = hash_password(demo["default_pass"])
                    update_fields["hashed_password"] = hash_password(demo["default_pass"])
                    update_fields["plain_demo_pass"] = demo["default_pass"]

                await users_col.update_one(
                    {"_id": existing_user["_id"]},
                    {"$set": update_fields}
                )

            # Seed stubbed QuickBooks token in database collection so stock auth checks return connected
            qb_tokens_col = get_collection("quickbooks_tokens")
            now = datetime.utcnow()
            token_id = f"tok_{user_id}"
            await qb_tokens_col.update_one(
                {"user_id": user_id, "realm_id": f"demo_realm_{biz_id}"},
                {"$set": {
                    "_id": token_id,
                    "user_id": user_id,
                    "realm_id": f"demo_realm_{biz_id}",
                    "access_token": "demo_access_token",
                    "refresh_token": "demo_refresh_token",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "x_refresh_token_expires_in": 8640000,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now
                }},
                upsert=True
            )

            # Full 16-section profile definitions per spec docs
            profile_metas = {
                "demo-restaurant": {
                    "naics": "722511", "industry": "Restaurant / Pizzeria", "woman_owned": False, "veteran_owned": False, "minority_owned": False,
                    "locations": [{"id": "loc_1", "name": "5th Ave", "address": "247 5th Ave, Brooklyn NY 11215", "neighborhood": "Park Slope", "status": "active"}],
                    "goals": {"d90": "Stop weekend walk-aways, trim food cost 1pt", "m12": "Cash reserve to $60K"},
                    "bottleneck": "Oven throughput weekend nights"
                },
                "demo-retail": {
                    "naics": "453220", "industry": "Gift & Home Goods Retail", "woman_owned": True, "veteran_owned": False, "minority_owned": False,
                    "locations": [{"id": "loc_1", "name": "Main St", "address": "118 N Main St, Asheville NC 28801", "neighborhood": "Downtown", "status": "active"}],
                    "goals": {"d90": "Pre-buy holiday inventory without cash crunch", "m12": "Second seasonal kiosk"},
                    "bottleneck": "Owner does all buying"
                },
                "demo-service": {
                    "naics": "238220", "industry": "Residential Plumbing & Heating", "woman_owned": False, "veteran_owned": True, "minority_owned": False,
                    "locations": [{"id": "loc_1", "name": "Shop", "address": "2240 Refugee Rd, Columbus OH 43207", "neighborhood": "South Side", "status": "active"}],
                    "goals": {"d90": "Cut AR days from 41 to 30", "m12": "Add 6th tech, $150K reserve"},
                    "bottleneck": "Licensed tech hours"
                },
                "demo-salon": {
                    "naics": "812112", "industry": "Hair Salon & Color Specialty", "woman_owned": True, "veteran_owned": False, "minority_owned": True,
                    "locations": [{"id": "loc_1", "name": "Logan Square", "address": "2734 W Fullerton Ave, Chicago IL 60647", "neighborhood": "Logan Square", "status": "active"}],
                    "goals": {"d90": "Fill Tue-Wed utilization from 55% to 70%", "m12": "Retail to 12% of revenue"},
                    "bottleneck": "Saturday chair hours"
                },
                "demo-multi": {
                    "naics": "722515", "industry": "Multi-location Cafe & Wholesale Roastery", "woman_owned": False, "veteran_owned": False, "minority_owned": True,
                    "locations": [
                        {"id": "alberta", "name": "Alberta St (Flagship)", "address": "1712 NE Alberta St, Portland OR 97211", "neighborhood": "Alberta Arts", "status": "active"},
                        {"id": "division", "name": "Division St (Satellite)", "address": "3340 SE Division St, Portland OR 97202", "neighborhood": "Richmond", "status": "active"}
                    ],
                    "goals": {"d90": "Division to breakeven", "m12": "Wholesale from 22% to 35% of revenue"},
                    "bottleneck": "One head roaster"
                },
                "demo-ecomm": {
                    "naics": "339999", "industry": "Shopify DTC Ecommerce", "woman_owned": True, "veteran_owned": False, "minority_owned": False,
                    "locations": [{"id": "loc_1", "name": "Production Studio", "address": "940 Wealthy St SE, Grand Rapids MI 49506", "neighborhood": "Eastown", "status": "active"}],
                    "goals": {"d90": "Get ROAS back above 3.2", "m12": "Email to 40% of revenue"},
                    "bottleneck": "Pour capacity in November"
                },
                "demo-fitness": {
                    "naics": "713940", "industry": "Group Fitness Studio", "woman_owned": False, "veteran_owned": False, "minority_owned": True,
                    "locations": [{"id": "loc_1", "name": "Studio", "address": "4110 S MacDill Ave, Tampa FL 33611", "neighborhood": "Ballast Point", "status": "active"}],
                    "goals": {"d90": "Churn under 4%/mo", "m12": "380 members from 342"},
                    "bottleneck": "Peak-slot class caps"
                }
            }

            # Load business profile verbatim from config if present
            biz_config = configs.get(biz_id, {})
            meta_profile = profile_metas.get(biz_id, {})
            profile_doc = {
                "user_id": user_id,
                "business_id": biz_id,
                "business_name": name,
                "monthly_revenue_base": biz_config.get("monthly_revenue_base", 50000),
                "naics_code": meta_profile.get("naics"),
                "industry": meta_profile.get("industry"),
                "woman_owned": meta_profile.get("woman_owned", False),
                "veteran_owned": meta_profile.get("veteran_owned", False),
                "minority_owned": meta_profile.get("minority_owned", False),
                "locations": meta_profile.get("locations", []),
                "goals": meta_profile.get("goals", {}),
                "bottlenecks": [meta_profile.get("bottleneck")] if meta_profile.get("bottleneck") else [],
                "is_demo": True,
                "updated_at": datetime.utcnow()
            }
            await profiles_col.update_one(
                {"user_id": user_id},
                {"$set": profile_doc},
                upsert=True
            )

            # Backfill 24 months history & emit daily data
            await demo_generator_service.run_history_backfill(
                biz_id=biz_id,
                user_id=user_id,
                epoch=epoch_date,
                months=backfill_months
            )

            # Addendum v3 Historical Replay Pass (Memory & Resolved Signals Seeding)
            from app.services.demo_replay_service import demo_replay_service
            await demo_replay_service.run_historical_replay(
                biz_id=biz_id,
                user_id=user_id,
                epoch=epoch_date
            )

            results.append({
                "biz_id": biz_id,
                "name": name,
                "email": email,
                "user_id": user_id,
                "status": "provisioned"
            })

        return results

    async def get_demo_health_status(self) -> List[Dict[str, Any]]:
        users_col = get_collection("users")
        qbo_col = get_collection("qbo_transactions")
        connector_col = get_collection("connector_statuses")
        memory_col = get_collection("customer_memory")

        health_list = []
        for demo in DEMO_ACCOUNTS_MAP:
            biz_id = demo["biz_id"]
            email = demo["email"]

            user = await users_col.find_one({"email": email})
            if not user:
                health_list.append({
                    "biz_id": biz_id,
                    "name": demo["name"],
                    "email": email,
                    "status_dot": "red",
                    "status_text": "Not Provisioned",
                    "last_sync": None
                })
                continue

            user_id = user.get("id", str(user.get("_id")))
            tx_count = await qbo_col.count_documents({"user_id": user_id})
            mem_count = await memory_col.count_documents({"user_id": user_id})
            connector = await connector_col.find_one({"user_id": user_id})

            if tx_count > 0 and connector and mem_count > 0:
                status_dot = "green"
                status_text = f"Healthy ({tx_count} records, {mem_count} memories)"
            elif tx_count > 0:
                status_dot = "amber"
                status_text = f"Data present ({tx_count} records), memory pending"
            else:
                status_dot = "red"
                status_text = "No records"

            last_sync = connector.get("updated_at") if connector else None
            last_sync_str = last_sync.isoformat() if isinstance(last_sync, datetime) else str(last_sync) if last_sync else None

            health_list.append({
                "biz_id": biz_id,
                "name": demo["name"],
                "email": email,
                "user_id": user_id,
                "status_dot": status_dot,
                "status_text": status_text,
                "records_count": tx_count,
                "memory_count": mem_count,
                "last_sync": last_sync_str
            })

        return health_list

    async def reset_demo_account(self, biz_id: str) -> Dict[str, Any]:
        target = next((d for d in DEMO_ACCOUNTS_MAP if d["biz_id"] == biz_id), None)
        if not target:
            raise ValueError(f"Unknown demo business ID: {biz_id}")

        users_col = get_collection("users")
        user = await users_col.find_one({"email": target["email"]})
        if user:
            user_id = user.get("id", str(user.get("_id")))
            epoch_date = date(2026, 7, 1)
            await demo_generator_service.run_history_backfill(
                biz_id=biz_id,
                user_id=user_id,
                epoch=epoch_date,
                months=24
            )
            from app.services.demo_replay_service import demo_replay_service
            await demo_replay_service.run_historical_replay(
                biz_id=biz_id,
                user_id=user_id,
                epoch=epoch_date
            )
            return {"status": "success", "message": f"Demo account {biz_id} reset and re-provisioned cleanly with Addendum v3 historical replay."}
        else:
            await self.provision_all_demo_accounts(backfill_months=24)
            return {"status": "success", "message": f"Demo accounts provisioned."}

demo_account_service = DemoAccountService()
