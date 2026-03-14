# ABOUTME: Celery task for running HDBSCAN clustering and duplicate detection.
# ABOUTME: Reads embeddings from PostgreSQL, clusters via scikit-learn, stores results.

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.celery_app import celery
from app.db.session import task_session
from app.models.job import Job, JobStatus, JobType
from app.services.cluster_service import run_clustering

logger = logging.getLogger(__name__)


async def _create_scheduled_job() -> str:
    job_id = uuid.uuid4()
    async with task_session() as session:
        job = Job(
            id=job_id,
            job_type=JobType.cluster_notes,
            parameters={"scheduled": True},
            status=JobStatus.pending,
        )
        session.add(job)
        await session.commit()
    return str(job_id)


async def _run_clustering(job_id: str | None, target_path: str, parameters: dict | None):
    try:
        if not job_id:
            job_id = await _create_scheduled_job()

        async with task_session() as session:
            job = await session.get(Job, job_id)
            if not job:
                return
            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            await session.commit()

        params = parameters or {}
        min_cluster_size = params.get("min_cluster_size")
        duplicate_threshold = params.get("duplicate_threshold")

        async def progress_callback(current: int, total: int):
            async with task_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.progress_current = current
                    job.progress_total = total
                    await session.commit()

        async with task_session() as session:
            stats = await run_clustering(
                session=session,
                job_id=job_id,
                min_cluster_size=min_cluster_size,
                duplicate_threshold=duplicate_threshold,
                progress_callback=progress_callback,
            )
            await session.commit()

        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.result = stats
                await session.commit()

    except Exception as exc:
        logger.exception("Clustering job failed")
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.failed
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()


@celery.task(bind=True, name="cluster_notes")
def cluster_notes(self, job_id: str, target_path: str, parameters: dict | None = None):
    asyncio.run(_run_clustering(job_id, target_path, parameters))
