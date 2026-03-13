# ABOUTME: Celery task for running auto-triage scans with progress tracking.
# ABOUTME: Detects convention violations, auto-applies low-risk fixes, queues high-risk suggestions.

import asyncio
import uuid
from datetime import datetime, timezone

from app.celery_app import celery
from app.db.session import task_session
from app.models.job import Job, JobStatus, JobType
from app.services.obsidian_client import ObsidianClient
from app.services.triage_service import run_triage_scan


async def _create_scheduled_job(scope: str) -> str:
    """Create a Job record for beat-triggered scans (no pre-existing job)."""
    job_id = uuid.uuid4()
    async with task_session() as session:
        job = Job(
            id=job_id,
            job_type=JobType.triage_scan,
            target_path=scope,
            parameters={"scan_type": "triage", "scheduled": True},
            status=JobStatus.pending,
        )
        session.add(job)
        await session.commit()
    return str(job_id)


async def _run_triage_scan(job_id: str | None, target_path: str, parameters: dict | None):
    client = ObsidianClient()
    try:
        scope = target_path or "/"

        if not job_id:
            job_id = await _create_scheduled_job(scope)

        async with task_session() as session:
            job = await session.get(Job, job_id)
            if not job:
                return
            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            await session.commit()

        async def update_progress(current: int, total: int):
            async with task_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.progress_current = current
                    job.progress_total = total
                    await session.commit()

        result = await run_triage_scan(scope, client, task_session, progress_callback=update_progress)

        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.result = {
                    "notes_scanned": result["notes_scanned"],
                    "issues_found": result["issues_found"],
                    "fixes_applied": result["fixes_applied"],
                    "suggestions_queued": result["suggestions_queued"],
                }
                await session.commit()

    except Exception as exc:
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.failed
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
    finally:
        await client.close()


@celery.task(bind=True, name="triage_scan")
def triage_scan(self, job_id: str, target_path: str, parameters: dict | None = None):
    asyncio.run(_run_triage_scan(job_id, target_path, parameters))
