# ABOUTME: Service for creating, querying, and managing background jobs.
# ABOUTME: Handles idempotency dedup for scan/cleanup jobs and Celery task lifecycle.

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, JobType


def compute_job_idempotency_key(job_type: str, target_path: str | None, parameters: dict | None) -> str:
    data = json.dumps({"type": job_type, "path": target_path, "params": parameters}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:64]


async def find_active_duplicate(session: AsyncSession, idempotency_key: str) -> Job | None:
    result = await session.scalar(
        select(Job).where(
            Job.idempotency_key == idempotency_key,
            Job.status.in_([JobStatus.pending, JobStatus.running]),
        )
    )
    return result


async def create_job(
    session: AsyncSession,
    job_type: str,
    target_path: str | None = None,
    parameters: dict | None = None,
    celery_task_id: str | None = None,
) -> tuple[Job, bool]:
    """Create a job with dedup check. Returns (job, is_new)."""
    dedup_types = {JobType.vault_scan, JobType.vault_cleanup}
    jt = JobType(job_type)
    idempotency_key = None

    if jt in dedup_types:
        idempotency_key = compute_job_idempotency_key(job_type, target_path, parameters)
        existing = await find_active_duplicate(session, idempotency_key)
        if existing:
            return existing, False

    job = Job(
        job_type=jt,
        target_path=target_path,
        parameters=parameters,
        idempotency_key=idempotency_key,
        celery_task_id=celery_task_id,
        status=JobStatus.pending,
    )
    session.add(job)
    await session.flush()
    return job, True


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await session.get(Job, job_id)


async def list_jobs(
    session: AsyncSession,
    status: str | None = None,
    job_type: str | None = None,
    since: datetime | None = None,
    limit: int = 50,
) -> tuple[list[Job], int]:
    query = select(Job)
    count_query = select(func.count()).select_from(Job)

    if status:
        query = query.where(Job.status == JobStatus(status))
        count_query = count_query.where(Job.status == JobStatus(status))
    if job_type:
        query = query.where(Job.job_type == JobType(job_type))
        count_query = count_query.where(Job.job_type == JobType(job_type))
    if since:
        query = query.where(Job.created_at >= since)
        count_query = count_query.where(Job.created_at >= since)

    total = await session.scalar(count_query) or 0
    query = query.order_by(Job.created_at.desc()).limit(limit)
    result = await session.execute(query)
    jobs = list(result.scalars().all())

    return jobs, total


async def cancel_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    job = await session.get(Job, job_id)
    if not job:
        return None
    if job.status not in (JobStatus.pending, JobStatus.running):
        return job
    job.status = JobStatus.cancelled
    job.completed_at = datetime.now(timezone.utc)
    await session.flush()
    return job
