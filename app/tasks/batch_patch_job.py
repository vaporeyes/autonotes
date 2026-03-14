# ABOUTME: Celery task for running batch patch operations asynchronously.
# ABOUTME: Handles large batches (>10 notes) with progress tracking and result storage.

import asyncio
import logging
from datetime import datetime, timezone

from app.celery_app import celery
from app.db.session import task_session
from app.models.job import Job, JobStatus
from app.schemas.patch import PatchOperationRequest
from app.services.batch_patch_service import (
    apply_batch,
    list_target_notes,
    list_target_notes_by_query,
)

logger = logging.getLogger(__name__)


async def _run_batch_patch(job_id: str, parameters: dict):
    try:
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if not job:
                return
            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            await session.commit()

        # Resolve target notes
        folder_path = parameters.get("folder_path")
        query = parameters.get("query")
        recursive = parameters.get("recursive", False)
        threshold = parameters.get("threshold", 0.5)
        limit = parameters.get("limit")

        if folder_path:
            note_paths = await list_target_notes(folder_path, recursive=recursive)
        elif query:
            async with task_session() as session:
                note_paths = await list_target_notes_by_query(
                    session, query, threshold=threshold, limit=limit
                )
        else:
            raise ValueError("No folder_path or query in parameters")

        # Update progress total
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.progress_current = 0
                job.progress_total = len(note_paths)
                await session.commit()

        # Build operation list
        ops_raw = parameters.get("operations", [])
        operations = [PatchOperationRequest(**op) for op in ops_raw]

        async def progress_callback(current: int, total: int):
            async with task_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.progress_current = current
                    job.progress_total = total
                    await session.commit()

        # Apply batch
        async with task_session() as session:
            job = await session.get(Job, job_id)
            result = await apply_batch(
                session, note_paths, operations,
                dry_run=False, job=job,
                progress_callback=progress_callback,
            )
            await session.commit()

        # Mark complete
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.result = result.model_dump()
                await session.commit()

    except Exception as exc:
        logger.exception("Batch patch job failed")
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.failed
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()


@celery.task(bind=True, name="batch_patch")
def batch_patch(self, job_id: str, target_path: str, parameters: dict | None = None):
    asyncio.run(_run_batch_patch(job_id, parameters or {}))
