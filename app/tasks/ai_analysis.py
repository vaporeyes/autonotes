# ABOUTME: Celery task for background LLM-powered note analysis.
# ABOUTME: Wraps ai_service.analyze with job progress tracking.

import asyncio
from datetime import datetime, timezone

from app.celery_app import celery
from app.db.session import task_session
from app.models.job import Job, JobStatus
from app.services import ai_service


async def _run_analysis(job_id: str, target_path: str, analysis_type: str):
    async with task_session() as session:
        job = await session.get(Job, job_id)
        if not job:
            return
        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

    try:
        async with task_session() as session:
            result = await ai_service.analyze(target_path, analysis_type, session, job_id=job_id)
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.result = result
            await session.commit()
    except Exception as exc:
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.failed
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
            await session.commit()


@celery.task(bind=True, name="ai_analysis")
def ai_analysis(self, job_id: str, target_path: str, analysis_type: str):
    asyncio.run(_run_analysis(job_id, target_path, analysis_type))
