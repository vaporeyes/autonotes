# ABOUTME: Celery task for running vault-wide note embedding with progress tracking.
# ABOUTME: Reads notes via Obsidian client, embeds via OpenAI, stores in PostgreSQL with pgvector.

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.celery_app import celery
from app.config import settings
from app.db.session import task_session
from app.models.job import Job, JobStatus, JobType
from app.services.embedding_service import embed_notes_batch
from app.services.obsidian_client import ObsidianClient

logger = logging.getLogger(__name__)


def _is_excluded(note_path: str) -> bool:
    """Check if a note path matches any exclusion pattern."""
    patterns = [p.strip() for p in settings.embedding_exclude_patterns.split(",") if p.strip()]
    for pattern in patterns:
        if note_path.startswith(pattern):
            return True
    return False


async def _create_scheduled_job(scope: str) -> str:
    job_id = uuid.uuid4()
    async with task_session() as session:
        job = Job(
            id=job_id,
            job_type=JobType.embed_notes,
            target_path=scope,
            parameters={"scheduled": True},
            status=JobStatus.pending,
        )
        session.add(job)
        await session.commit()
    return str(job_id)


async def _run_embedding(job_id: str | None, target_path: str, parameters: dict | None):
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

        # List all .md files in scope
        all_files = await client.list_folder(scope.rstrip("/") or "", recursive=True)
        md_files = [f for f in all_files if f.endswith(".md") and not _is_excluded(f)]

        # Read all note contents
        notes = []
        for file_path in md_files:
            try:
                raw = await client.get_note_raw(file_path)
                notes.append((file_path, raw))
            except Exception:
                logger.warning("Failed to read note: %s", file_path)

        # Update total
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.progress_current = 0
                job.progress_total = len(notes)
                await session.commit()

        # Embed in a single session
        async def progress_callback(current: int, total: int):
            async with task_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.progress_current = current
                    job.progress_total = total
                    await session.commit()

        async with task_session() as session:
            stats = await embed_notes_batch(session, notes, progress_callback=progress_callback)
            await session.commit()

        # Mark complete
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.result = stats
                await session.commit()

    except Exception as exc:
        logger.exception("Embedding job failed")
        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.failed
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
    finally:
        await client.close()


@celery.task(bind=True, name="embed_notes")
def embed_notes(self, job_id: str, target_path: str, parameters: dict | None = None):
    asyncio.run(_run_embedding(job_id, target_path, parameters))
