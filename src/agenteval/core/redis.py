"""Redis client singleton"""

import redis.asyncio as redis
import structlog

from agenteval.core.config import get_settings

logger = structlog.get_logger()

_redis_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or create Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_pool


async def check_redis() -> bool:
    """Check Redis connectivity"""
    try:
        r = await get_redis()
        return await r.ping()
    except Exception as e:
        logger.error("redis.check.failed", error=str(e))
        return False


async def close_redis() -> None:
    """Close Redis connection pool"""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None
