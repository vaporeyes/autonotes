# ABOUTME: Health check endpoint verifying Obsidian API, Redis, and Postgres connectivity.
# ABOUTME: Returns per-service status and count of active jobs.

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.models.job import Job, JobStatus
from app.services.obsidian_client import obsidian_client

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
    except Exception:
        result["status"] = "degraded"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        result["redis"] = "connected"
    except Exception:
        result["status"] = "degraded"

    # Postgres + active jobs count
    try:
        count = await session.scalar(
            select(func.count()).select_from(Job).where(
                Job.status.in_([JobStatus.pending, JobStatus.running])
            )
        )
        result["postgres"] = "connected"
        result["active_jobs"] = count or 0
    except Exception:
        result["status"] = "degraded"

    return result
