# ABOUTME: Service for creating and querying operation log entries.
# ABOUTME: Supports filtered queries and retention-based purge for old entries.

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.operation_log import LogStatus, OperationLog


async def create_log(
    session: AsyncSession,
    operation_name: str,
    target_path: str,
    status: LogStatus,
    job_id: uuid.UUID | None = None,
    patch_operation_id: uuid.UUID | None = None,
    before_hash: str | None = None,
    after_hash: str | None = None,
    error_message: str | None = None,
    llm_notes_sent: list[str] | None = None,
) -> OperationLog:
    log = OperationLog(
        job_id=job_id,
        patch_operation_id=patch_operation_id,
        operation_name=operation_name,
        target_path=target_path,
        before_hash=before_hash,
        after_hash=after_hash,
        status=status,
        error_message=error_message,
        llm_notes_sent=llm_notes_sent,
    )
    session.add(log)
    await session.flush()
    return log


async def query_logs(
    session: AsyncSession,
    target_path: str | None = None,
    operation_name: str | None = None,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
) -> tuple[list[OperationLog], int]:
    query = select(OperationLog)
    count_query = select(func.count()).select_from(OperationLog)

    if target_path:
        query = query.where(OperationLog.target_path == target_path)
        count_query = count_query.where(OperationLog.target_path == target_path)
    if operation_name:
        query = query.where(OperationLog.operation_name == operation_name)
        count_query = count_query.where(OperationLog.operation_name == operation_name)
    if status:
        query = query.where(OperationLog.status == LogStatus(status))
        count_query = count_query.where(OperationLog.status == LogStatus(status))
    if since:
        query = query.where(OperationLog.created_at >= since)
        count_query = count_query.where(OperationLog.created_at >= since)
    if until:
        query = query.where(OperationLog.created_at <= until)
        count_query = count_query.where(OperationLog.created_at <= until)

    total = await session.scalar(count_query) or 0
    query = query.order_by(OperationLog.created_at.desc()).limit(limit)
    result = await session.execute(query)
    logs = list(result.scalars().all())

    return logs, total


async def purge_old_logs(session: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.log_retention_days)
    result = await session.execute(
        delete(OperationLog).where(OperationLog.created_at < cutoff)
    )
    await session.flush()
    return result.rowcount
