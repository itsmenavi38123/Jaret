# backend/app/db.py
import os
import certifi
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    """
    Returns a singleton AsyncIOMotorClient. Creates it if not already created.
    """
    global _client
    if _client is None:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError("MONGO_URI not set in environment")
        # Use certifi for SSL certificates to avoid handshake errors
        _client = AsyncIOMotorClient(mongo_uri, tlsCAFile=certifi.where())
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """
    Returns the configured database object.
    """
    global _db
    if _db is None:
        db_name = os.getenv("MONGO_DB_NAME")
        if not db_name:
            raise RuntimeError("MONGO_DB_NAME not set in environment")
        _db = get_client()[db_name]
    return _db


def get_collection(name: str) -> AsyncIOMotorCollection:
    """
    Convenience to get a collection from the configured DB.
    Usage: users = get_collection('users'); await users.find_one({...})
    """
    return get_database()[name]


def close_client() -> None:
    """
    Close the motor client - call this on application shutdown.
    """
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

    # Assets (built-in Asset Hub and external sync target)
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

    admin_logs = get_collection("admin_logs")
    await admin_logs.create_index("admin_user_id")
    await admin_logs.create_index("target_user_id")
    await admin_logs.create_index("action")
    await admin_logs.create_index("timestamp")
    await admin_logs.create_index([("admin_user_id", 1), ("timestamp", -1)])
    await admin_logs.create_index([("target_user_id", 1), ("timestamp", -1)])

    # Scenario planning chat threads
    scenario_chats = get_collection("scenario_chats")
    await scenario_chats.create_index("user_id")
    await scenario_chats.create_index("created_at")
    await scenario_chats.create_index([("user_id", 1), ("updated_at", -1)])