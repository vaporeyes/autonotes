# ABOUTME: Celery task for running vault health scans with progress tracking.
# ABOUTME: Computes metrics via health_service and persists a HealthSnapshot to PostgreSQL.

import asyncio
import uuid
from datetime import datetime, timezone

from app.celery_app import celery
from app.db.session import task_session
from app.models.health_snapshot import HealthSnapshot
from app.models.job import Job, JobStatus, JobType
from app.services.health_service import purge_old_snapshots, run_health_scan
from app.services.obsidian_client import ObsidianClient


async def _create_scheduled_job(scope: str) -> str:
    """Create a Job record for beat-triggered scans (no pre-existing job)."""
    job_id = uuid.uuid4()
    async with task_session() as session:
        job = Job(
            id=job_id,
            job_type=JobType.vault_health_scan,
            target_path=scope,
            parameters={"scan_type": "vault_health", "scheduled": True},
            status=JobStatus.pending,
        )
        session.add(job)
        await session.commit()
    return str(job_id)


async def _run_health_scan(job_id: str | None, target_path: str, parameters: dict | None):
    client = ObsidianClient()
    try:
        scope = target_path or "/"

        # Beat-triggered: create a job record first
        if not job_id:
            job_id = await _create_scheduled_job(scope)

        async with task_session() as session:
            job = await session.get(Job, job_id)
            if not job:
                return
            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            await session.commit()

        # Progress callback updates the job record
        async def update_progress(current: int, total: int):
            async with task_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.progress_current = current
                    job.progress_total = total
                    await session.commit()

        metrics = await run_health_scan(scope, client, progress_callback=update_progress)

        # Persist the snapshot and mark job complete
        async with task_session() as session:
            snapshot = HealthSnapshot(
                id=uuid.uuid4(),
                job_id=uuid.UUID(job_id),
                scan_scope=metrics["scan_scope"],
                total_notes=metrics["total_notes"],
                orphan_count=metrics["orphan_count"],
                orphan_paths=metrics["orphan_paths"],
                zero_outbound_paths=metrics["zero_outbound_paths"],
                tag_distribution=metrics["tag_distribution"],
                unique_tag_count=metrics["unique_tag_count"],
                backlink_density=metrics["backlink_density"],
                cluster_count=metrics["cluster_count"],
                cluster_sizes=metrics["cluster_sizes"],
                health_score=metrics["health_score"],
                skipped_notes=metrics["skipped_notes"],
            )
            session.add(snapshot)

            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.result = {
                    "total_notes": metrics["total_notes"],
                    "orphan_count": metrics["orphan_count"],
                    "backlink_density": metrics["backlink_density"],
                    "cluster_count": metrics["cluster_count"],
                    "health_score": metrics["health_score"],
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


@celery.task(bind=True, name="vault_health_scan")
def vault_health_scan(self, job_id: str, target_path: str, parameters: dict | None = None):
    asyncio.run(_run_health_scan(job_id, target_path, parameters))


# -- Snapshot purge beat task (US4) --

async def _purge_snapshots():
    async with task_session() as session:
        count = await purge_old_snapshots(session)
        return count


@celery.task(name="health_snapshot_purge")
def health_snapshot_purge():
    return asyncio.run(_purge_snapshots())
