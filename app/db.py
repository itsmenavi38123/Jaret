# backend/app/db.py
import os
import certifi
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

from motor.motor_asyncio import AsyncIOMotorGridFSBucket

def get_gridfs_bucket():
    return AsyncIOMotorGridFSBucket(get_database())

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError("MONGO_URI not set in environment")
        _client = AsyncIOMotorClient(
            mongo_uri,
            tlsCAFile=certifi.where(),
        )
    return _client


def get_database() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        db_name = os.getenv("MONGO_DB_NAME")
        if not db_name:
            raise RuntimeError("MONGO_DB_NAME not set in environment")
        _db = get_client()[db_name]
    return _db


def get_collection(name: str) -> AsyncIOMotorCollection:
    return get_database()[name]


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def create_indexes() -> None:

    users = get_collection("users")
    await users.create_index("email", unique=True)

    business_profiles = get_collection("business_profiles")
    await business_profiles.create_index("user_id", unique=True)
    await business_profiles.create_index("created_at")
    await business_profiles.create_index("updated_at")

    quickbooks_tokens = get_collection("quickbooks_tokens")
    await quickbooks_tokens.create_index("user_id")
    await quickbooks_tokens.create_index("realm_id")
    await quickbooks_tokens.create_index([("user_id", 1), ("realm_id", 1)])
    await quickbooks_tokens.create_index([("user_id", 1), ("is_active", 1)])
    await quickbooks_tokens.create_index("created_at")

    xero_tokens = get_collection("xero_tokens")
    await xero_tokens.create_index("user_id")
    await xero_tokens.create_index("tenant_id")
    await xero_tokens.create_index([("user_id", 1), ("tenant_id", 1)])
    await xero_tokens.create_index([("user_id", 1), ("is_active", 1)])
    await xero_tokens.create_index("created_at")

    assets = get_collection("assets")
    await assets.create_index("user_id")
    await assets.create_index("asset_id")

    manual_entries = get_collection("manual_entries")
    await manual_entries.create_index([("user_id", 1), ("occurred_on", 1)])

    reminders = get_collection("reminders")
    await reminders.create_index([("user_id", 1), ("due_date", 1)])

    opportunities = get_collection("opportunities")
    await opportunities.create_index("user_id")
    await opportunities.create_index("status")
    await opportunities.create_index("deadline")
    await opportunities.create_index("created_at")
    await opportunities.create_index("updated_at")
    await opportunities.create_index("opportunity_type")
    await opportunities.create_index("scoring_data.match_score")
    await opportunities.create_index([("user_id", 1), ("deadline", 1)])

    scout_runs = get_collection("scout_runs")
    await scout_runs.create_index("business_id")
    await scout_runs.create_index("started_at")

    scout_rate_limits = get_collection("scout_rate_limits")
    await scout_rate_limits.create_index([("business_id", 1), ("date", 1)])

    execution_checkpoints = get_collection("execution_checkpoints")
    await execution_checkpoints.create_index("opportunity_id")
    await execution_checkpoints.create_index("scheduled_at")

    admin_logs = get_collection("admin_logs")
    await admin_logs.create_index("admin_user_id")
    await admin_logs.create_index("target_user_id")
    await admin_logs.create_index("action")
    await admin_logs.create_index("timestamp")
    await admin_logs.create_index([("admin_user_id", 1), ("timestamp", -1)])
    await admin_logs.create_index([("target_user_id", 1), ("timestamp", -1)])

    scenario_chats = get_collection("scenario_chats")
    await scenario_chats.create_index("user_id")
    await scenario_chats.create_index("created_at")
    await scenario_chats.create_index([("user_id", 1), ("updated_at", -1)])

    benchmarks = get_collection("benchmarks")
    await benchmarks.create_index([("metric_key", 1), ("classifier.industry", 1), ("classifier.country", 1), ("classifier.revenue_band", 1)])
    await benchmarks.create_index([("metric_key", 1), ("source", 1)])
    await benchmarks.create_index([("classifier.industry", 1), ("classifier.country", 1), ("classifier.revenue_band", 1)])

    user_pos_access = get_collection("user_pos_access")
    await user_pos_access.create_index([("user_id", 1), ("provider", 1)], unique=True)

    oauth_states = get_collection("oauth_states")
    await oauth_states.create_index("state", unique=True)

    customer_memory = get_collection("customer_memory")
    await customer_memory.create_index("user_id")
    await customer_memory.create_index("path")
    await customer_memory.create_index("observation_type")
    await customer_memory.create_index("created_at")
    await customer_memory.create_index([("user_id", 1), ("created_at", -1)])
    await customer_memory.create_index([("user_id", 1), ("outdated", 1)])

    org_playbook = get_collection("org_playbook")
    await org_playbook.create_index("path")
    await org_playbook.create_index("source_type")
    await org_playbook.create_index("observation_type")
    await org_playbook.create_index("created_at")

    kpi_preferences = get_collection("financial_overview_kpi_preferences")
    await kpi_preferences.create_index("user_id",unique=True)

    notification_settings = get_collection("notification_settings")
    await notification_settings.create_index("user_id", unique=True)
    await kpi_preferences.create_index("updated_at")

    password_reset_tokens = get_collection("password_reset_tokens")
    await password_reset_tokens.create_index("user_id")
    await password_reset_tokens.create_index("token_hash", unique=True)
    await password_reset_tokens.create_index("expires_at")