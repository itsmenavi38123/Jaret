# backend/app/services/demo_replay_service.py
import json
import os
import asyncio
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from app.db import get_collection

class DemoReplayService:
    async def run_historical_replay(self, biz_id: str, user_id: str, epoch: date = date(2026, 7, 1)) -> Dict[str, Any]:
        """
        Executes the Addendum v3 Historical Replay pass for a demo account.
        Walks backward 365 days, stepping through nightly cycles to populate 
        customer_memory and generate green-checkmark resolved signals.
        """
        memory_col = get_collection("customer_memory")
        signals_col = get_collection("resolved_signals")
        playbook_col = get_collection("org_playbook")

        # Clean existing demo memories & resolved signals for clean replay
        await memory_col.delete_many({"user_id": user_id})
        await signals_col.delete_many({"user_id": user_id})
        await playbook_col.delete_many({"user_id": user_id})

        start_date = epoch - timedelta(days=365)

        memories_written = 0
        resolved_written = 0

        # Load business config dynamically from Jaret's JSON spec files
        from app.services.demo_generator_service import demo_generator_service
        configs = demo_generator_service.load_configs()
        biz_config = configs.get(biz_id, {})
        anomalies = biz_config.get("anomalies", [])

        now = datetime.utcnow()

        for idx, anomaly in enumerate(anomalies):
            wk_start = anomaly.get("wk", [1, 2])[0]
            offset_days = (wk_start * 25) + 15  # Distribute across 365-day backfill window
            evt_date = start_date + timedelta(days=offset_days)
            evt_dt = datetime.combine(evt_date, datetime.min.time())

            story = anomaly.get("story", f"Observed anomaly {anomaly.get('id')}")
            title = story.capitalize()

            # Write memory record
            mem_doc = {
                "_id": f"mem_{user_id}_{idx+1}",
                "user_id": user_id,
                "business_id": biz_id,
                "observation_type": "pattern" if idx % 2 == 0 else "learning",
                "path_prefix": "margin.cogs" if ("cost" in story or "vendor" in story or "pass-through" in story) else "operations.capacity",
                "title": title,
                "content": f"Historical anomaly pattern detected: {story}. Verified against daily POS and accounting ledger records.",
                "outdated": False,
                "is_demo": True,
                "replay_mode": True,
                "created_at": evt_dt,
                "updated_at": evt_dt
            }
            await memory_col.insert_one(mem_doc)
            memories_written += 1

            # Write resolved signal card
            res_days_old = max(30, 280 - (idx * 70))
            res_date = now - timedelta(days=res_days_old)
            sig_doc = {
                "_id": f"sig_{user_id}_{idx+1}",
                "user_id": user_id,
                "business_id": biz_id,
                "title": title,
                "category": "Margin Compression" if ("cost" in story or "vendor" in story or "pass-through" in story) else "Capacity Bottleneck",
                "status": "resolved",
                "resolved_at": res_date,
                "resolve_days_old": res_days_old,
                "resolution_note": f"Operational resolution applied: {story} resolved.",
                "is_demo": True,
                "created_at": evt_dt
            }
            await signals_col.insert_one(sig_doc)
            resolved_written += 1

        print(f"[HISTORICAL REPLAY] Complete for {biz_id} ({user_id}): {memories_written} memories, {resolved_written} resolved signal cards written.")
        return {
            "status": "success",
            "business_id": biz_id,
            "user_id": user_id,
            "memories_written": memories_written,
            "resolved_signals_written": resolved_written
        }

demo_replay_service = DemoReplayService()
