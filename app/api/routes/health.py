# ABOUTME: Health check endpoint verifying Obsidian API, Redis, and Postgres connectivity.
# ABOUTME: Returns per-service status and count of active jobs.

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.models.job import Job, JobStatus
from app.services.obsidian_client import obsidian_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    result = {
        "status": "healthy",
        "obsidian_api": "disconnected",
        "redis": "disconnected",
        "postgres": "disconnected",
        "active_jobs": 0,
    }

    # Obsidian API
    try:
        await obsidian_client.health_check()
        result["obsidian_api"] = "connected"
    except Exception as exc:
        logger.warning("Obsidian API health check failed: %s", exc)
        result["status"] = "degraded"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        result["redis"] = "connected"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        result["status"] = "degraded"

    # Postgres connectivity (simple SELECT 1, no table dependency)
    try:
        await session.execute(text("SELECT 1"))
        result["postgres"] = "connected"
    except Exception as exc:
        logger.warning("Postgres health check failed: %s", exc)
        result["status"] = "degraded"

    # Active jobs count (only if postgres is connected and tables exist)
    if result["postgres"] == "connected":
        try:
            count = await session.scalar(
                select(func.count()).select_from(Job).where(
                    Job.status.in_([JobStatus.pending, JobStatus.running])
                )
            )
            result["active_jobs"] = count or 0
        except Exception:
            pass

    return result
