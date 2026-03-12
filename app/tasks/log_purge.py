# ABOUTME: Celery beat task for periodic purge of old operation log entries.
# ABOUTME: Deletes OperationLog records older than LOG_RETENTION_DAYS.

import asyncio

from app.celery_app import celery
from app.db.session import task_session
from app.services import log_service


async def _run_purge():
    async with task_session() as session:
        deleted = await log_service.purge_old_logs(session)
        await session.commit()
        return deleted


@celery.task(name="log_purge")
def log_purge():
    return asyncio.run(_run_purge())
