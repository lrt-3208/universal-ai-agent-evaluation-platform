"""Health check endpoint"""

from fastapi import APIRouter

from agenteval.core.database import check_database
from agenteval.core.redis import check_redis
from agenteval.core.response import success

router = APIRouter()


@router.get("/health")
async def health_check():
    """Service health check - verifies DB and Redis connectivity"""
    db_ok = await check_database()
    redis_ok = await check_redis()

    status = "ok" if (db_ok and redis_ok) else "degraded"

    return success(
        data={
            "status": status,
            "version": "0.1.0",
            "checks": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
        }
    )
"""Health check endpoint"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "ok",
        "version": "0.1.0",
        "checks": {
            "database": "ok",
            "redis": "ok",
        },
    }
