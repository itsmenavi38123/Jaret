# backend/app/db.py
import os
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
        _client = AsyncIOMotorClient(mongo_uri)
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
    
    quickbooks_tokens = get_collection("quickbooks_tokens")
    await quickbooks_tokens.create_index("user_id")
    await quickbooks_tokens.create_index("realm_id")
    await quickbooks_tokens.create_index([("user_id", 1), ("realm_id", 1)])
    await quickbooks_tokens.create_index([("user_id", 1), ("is_active", 1)])
    await quickbooks_tokens.create_index("created_at")
