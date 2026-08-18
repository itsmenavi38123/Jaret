# backend/app/services/demo_generator_service.py
import json
import os
import random
import hashlib
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from app.db import get_collection

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Demo Accounts")

class DemoGeneratorService:
    def __init__(self):
        self._config_cache: Optional[Dict[str, Any]] = None
        self._review_pools_cache: Optional[Dict[str, Any]] = None

    def load_configs(self) -> Dict[str, Any]:
        if self._config_cache is not None:
            return self._config_cache

        part1_path = os.path.join(CONFIG_DIR, "demo_generator_configs_v1_part1.json")
        part2_path = os.path.join(CONFIG_DIR, "demo_generator_configs_v1_part2.json")

        businesses = []
        if os.path.exists(part1_path):
            with open(part1_path, "r", encoding="utf-8") as f:
                d1 = json.load(f)
                businesses.extend(d1.get("businesses", []))
        if os.path.exists(part2_path):
            with open(part2_path, "r", encoding="utf-8") as f:
                d2 = json.load(f)
                businesses.extend(d2.get("businesses", []))

        self._config_cache = {b["business_id"]: b for b in businesses}
        return self._config_cache

    def load_review_pools(self) -> Dict[str, Any]:
        if self._review_pools_cache is not None:
            return self._review_pools_cache

        pool_path = os.path.join(CONFIG_DIR, "demo_review_pools_v1.json")
        if os.path.exists(pool_path):
            with open(pool_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._review_pools_cache = data.get("pools", {})
        else:
            self._review_pools_cache = {}
        return self._review_pools_cache

    def seeded_rng(self, business_id: str, d: date) -> random.Random:
        h = hashlib.sha256(f"{business_id}:{d.isoformat()}".encode()).hexdigest()
        return random.Random(int(h[:12], 16))

    def week_index(self, epoch: date, d: date) -> int:
        wk = ((d - epoch).days // 7) + 1
        return ((wk - 1) % 13) + 1

    def active_anomalies(self, biz: dict, wk: int) -> List[dict]:
        return [a for a in biz.get("anomalies", []) if a["wk"][0] <= wk <= a["wk"][1]]

    def rng_range(self, rng: random.Random, lo_hi: Any) -> float:
        if isinstance(lo_hi, (list, tuple)):
            lo, hi = lo_hi[0], lo_hi[1]
            return rng.uniform(lo, hi) if isinstance(lo, float) or isinstance(hi, float) else rng.randint(lo, hi)
        return float(lo_hi)

    def daily_revenue_target(self, biz: dict, d: date, rng: random.Random) -> float:
        monthly = biz["monthly_revenue_base"]
        season = biz["seasonality"][d.month - 1]
        dow_share = biz["weekly_curve"][d.weekday()]
        weekly = (monthly * 12 / 52.0) * season
        jitter = 1 + rng.uniform(-biz["jitter_pct"], biz["jitter_pct"]) / 100.0
        return weekly * dow_share * jitter

    def apply_anomaly_patches(self, biz: dict, anomalies: List[dict]) -> dict:
        import copy
        b = copy.deepcopy(biz)
        for a in anomalies:
            for path, val in a.get("effect", {}).items():
                if path in ("one_time_income", "one_time_expense", "day_override", "note",
                            "review_pool", "recurring_income_add"):
                    continue
                node = b
                keys = path.split(".")
                for k in keys[:-1]:
                    if isinstance(node, list):
                        node = next((x for x in node if x.get("id") == k), None) or {}
                    else:
                        node = node.get(k, {})
                if isinstance(node, dict):
                    node[keys[-1]] = val
        return b

    def emit_transactions(self, biz: dict, d: date, revenue: float, rng: random.Random, user_id: str) -> List[dict]:
        day_name = DAYS[d.weekday()]
        if day_name in biz.get("closed_days", []):
            return []
        records = []
        for stream in biz.get("streams", []):
            share = stream.get("share", 0)
            if share <= 0 or ("tx_count" not in stream and "orders_per_day" not in stream):
                continue
            stream_rev = revenue * share
            tc = stream.get("tx_count") or {}
            if "by_day" in tc:
                n = tc["by_day"].get(day_name, 0)
            elif "per_week" in tc:
                n = round(self.rng_range(rng, tc["per_week"]) / 5) if d.weekday() < 5 else 0
            elif "orders_per_day" in stream:
                n = self.rng_range(rng, stream["orders_per_day"]["baseline"])
            else:
                key = "weekend" if d.weekday() >= 5 else "weekday"
                n = self.rng_range(rng, tc.get(key, [0, 0]))
            n = max(0, int(n))
            if n == 0:
                continue
            mix = stream.get("ticket_mix", [{"label": "tx", "share": 1.0, "avg": stream_rev / max(n, 1)}])
            for _ in range(n):
                m = rng.choices(mix, weights=[x["share"] for x in mix])[0]
                avg = m.get("avg") or self.rng_range(rng, m.get("avg_range", [50, 100]))
                amt = round(max(1.0, rng.gauss(avg, avg * 0.18)), 2)
                rec = {
                    "user_id": user_id,
                    "business_id": biz["business_id"],
                    "stream": stream["id"],
                    "date": datetime.combine(d, datetime.min.time()),
                    "date_str": d.isoformat(),
                    "label": m["label"],
                    "amount": amt,
                    "is_demo": True
                }
                if "ar_terms" in stream:
                    actual = int(self.rng_range(rng, stream["ar_terms"]["actual_days"]))
                    rec["invoice"] = True
                    rec["due_date"] = (d + timedelta(days=stream["ar_terms"]["stated_days"])).isoformat()
                    rec["expected_payment_date"] = (d + timedelta(days=actual)).isoformat()
                records.append(rec)
        return records

    def emit_fixed_events(self, biz: dict, d: date, user_id: str) -> List[dict]:
        out = []
        for ev in biz.get("fixed_events", []):
            hit = False
            if ev.get("day_of_month") == d.day:
                hit = True
            elif ev.get("cadence") == "biweekly" and d.weekday() == 4 and (d.isocalendar().week % 2 == 0):
                hit = True
            if not hit:
                continue
            amt = ev.get("amount")
            if amt is None and "amount_pct_of_monthly_rev" in ev:
                amt = round(biz["monthly_revenue_base"] * ev["amount_pct_of_monthly_rev"] / 2, 2)
            out.append({
                "user_id": user_id,
                "business_id": biz["business_id"],
                "date": datetime.combine(d, datetime.min.time()),
                "date_str": d.isoformat(),
                "label": ev["label"],
                "amount": amt,
                "type": "fixed",
                "is_demo": True
            })
        return out

    def emit_reviews(self, biz: dict, d: date, rng: random.Random, anomalies: List[dict], user_id: str) -> List[dict]:
        out = []
        pools = self.load_review_pools().get(biz["business_id"], {})
        pool_override = None
        for a in anomalies:
            if "review_pool" in a.get("effect", {}):
                pool_override = a["effect"]["review_pool"]

        for platform, cfg in biz.get("reviews", {}).items():
            if rng.random() > (sum(cfg["per_week"]) / 2) / 7.0:
                continue
            stars = int(rng.choices(list(cfg["star_dist"].keys()),
                                    weights=list(cfg["star_dist"].values()))[0])
            pool_key = str(stars)
            texts = pools.get(pool_key, ["Great service!"])
            if pool_override and stars <= 3 and "anomaly_pools" in pools:
                texts = pools["anomaly_pools"].get(pool_override, texts)
            review_text = rng.choice(texts)
            reviewer_name = rng.choice(["Alex M.", "Sarah T.", "Dave R.", "Jessica K.", "Chris P.", "Amanda L.", "Michael B."])

            out.append({
                "user_id": user_id,
                "business_id": biz["business_id"],
                "date": datetime.combine(d, datetime.min.time()),
                "date_str": d.isoformat(),
                "platform": platform,
                "stars": stars,
                "reviewer_name": reviewer_name,
                "content": review_text,
                "is_demo": True
            })
        return out

    def generate_day_records(self, biz_id: str, user_id: str, d: date, epoch: date) -> dict:
        configs = self.load_configs()
        biz = configs.get(biz_id)
        if not biz:
            raise ValueError(f"Unknown demo business_id: {biz_id}")

        rng = self.seeded_rng(biz_id, d)
        wk = self.week_index(epoch, d)
        anomalies = self.active_anomalies(biz, wk)
        patched = self.apply_anomaly_patches(biz, anomalies)
        revenue = self.daily_revenue_target(patched, d, rng)

        extra = []
        for a in anomalies:
            eff = a.get("effect", {})
            if "revenue_mult" in eff:
                revenue *= eff["revenue_mult"]
            if "day_override" in eff and DAYS[d.weekday()] == eff["day_override"]["weekday"]:
                revenue *= eff["day_override"]["revenue_mult"]
            for key in ("one_time_income", "one_time_expense"):
                if key in eff and wk == a["wk"][0] and d.weekday() == 2:
                    extra.append({
                        "user_id": user_id,
                        "business_id": biz_id,
                        "date": datetime.combine(d, datetime.min.time()),
                        "date_str": d.isoformat(),
                        "label": eff[key]["label"],
                        "amount": eff[key]["amount"],
                        "type": "one_time",
                        "is_demo": True
                    })

        txs = self.emit_transactions(patched, d, revenue, rng, user_id)
        fixed = self.emit_fixed_events(patched, d, user_id)
        reviews = self.emit_reviews(patched, d, rng, anomalies, user_id)

        return {
            "transactions": txs,
            "fixed_events": fixed + extra,
            "reviews": reviews,
            "day_revenue_total": round(sum(t["amount"] for t in txs), 2)
        }

    async def ingest_day_records(self, biz_id: str, user_id: str, d: date, epoch: date):
        records = self.generate_day_records(biz_id, user_id, d, epoch)

        qbo_tx_col = get_collection("qbo_transactions")
        fixed_col = get_collection("fixed_expenses")
        reviews_col = get_collection("reviews")

        # Delete any existing demo records for this user+date to keep runs idempotent
        date_start = datetime.combine(d, datetime.min.time())
        date_end = datetime.combine(d, datetime.max.time())
        date_filter = {"user_id": user_id, "date": {"$gte": date_start, "$lte": date_end}}

        await qbo_tx_col.delete_many(date_filter)
        await fixed_col.delete_many(date_filter)
        await reviews_col.delete_many(date_filter)

        if records["transactions"]:
            await qbo_tx_col.insert_many(records["transactions"])
        if records["fixed_events"]:
            await fixed_col.insert_many(records["fixed_events"])
        if records["reviews"]:
            await reviews_col.insert_many(records["reviews"])

        # Update connector stub sync timestamp
        connector_col = get_collection("connector_statuses")
        now = datetime.utcnow()
        await connector_col.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "quickbooks": {"status": "connected", "last_sync": now},
                "pos": {"status": "connected", "last_sync": now},
                "updated_at": now
            }},
            upsert=True
        )

    async def run_history_backfill(self, biz_id: str, user_id: str, epoch: date, months: int = 24):
        today = date.today()
        start_date = today - timedelta(days=30 * months)
        curr = start_date

        qbo_tx_col = get_collection("qbo_transactions")
        fixed_col = get_collection("fixed_expenses")
        reviews_col = get_collection("reviews")
        connector_col = get_collection("connector_statuses")

        # Delete existing demo records for this user in range
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())
        user_filter = {"user_id": user_id, "date": {"$gte": start_dt, "$lte": end_dt}}

        await qbo_tx_col.delete_many(user_filter)
        await fixed_col.delete_many(user_filter)
        await reviews_col.delete_many(user_filter)

        all_txs = []
        all_fixed = []
        all_reviews = []
        count = 0

        while curr <= today:
            records = self.generate_day_records(biz_id, user_id, curr, epoch)
            all_txs.extend(records["transactions"])
            all_fixed.extend(records["fixed_events"])
            all_reviews.extend(records["reviews"])
            curr += timedelta(days=1)
            count += 1

        if all_txs:
            await qbo_tx_col.insert_many(all_txs)
        if all_fixed:
            await fixed_col.insert_many(all_fixed)
        if all_reviews:
            await reviews_col.insert_many(all_reviews)

        # Update connector stub sync timestamp
        now = datetime.utcnow()
        await connector_col.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "quickbooks": {"status": "connected", "last_sync": now},
                "pos": {"status": "connected", "last_sync": now},
                "updated_at": now
            }},
            upsert=True
        )

        print(f"[DEMO GENERATOR] Bulk backfill complete for {biz_id}: {count} days, {len(all_txs)} txs, {len(all_fixed)} fixed, {len(all_reviews)} reviews.")

demo_generator_service = DemoGeneratorService()
