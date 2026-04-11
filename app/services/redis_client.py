# backend/app/services/redis_client.py
"""
Redis Client Service
Provides singleton async Redis connection with error handling.
"""
import logging
from typing import Optional
import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

# Singleton Redis connection
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> Optional[redis.Redis]:
    """
    Get or create singleton Redis connection.
    
    Returns None if connection fails (graceful fallback).
    """
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    try:
        _redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )
        
        # Test connection
        await _redis_client.ping()
        logger.info("Redis connection established successfully")
        return _redis_client
        
    except Exception as exc:
        logger.warning(f"Failed to connect to Redis: {exc}. Caching disabled.")
        _redis_client = None
        return None


async def close_redis_client() -> None:
    """
    Close Redis connection gracefully.
    """
    global _redis_client
    
    if _redis_client is not None:
        try:
            await _redis_client.close()
            logger.info("Redis connection closed")
        except Exception as exc:
            logger.error(f"Error closing Redis connection: {exc}")
        finally:
            _redis_client = None
