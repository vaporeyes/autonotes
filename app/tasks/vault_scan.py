# ABOUTME: Celery task for scanning vault folders and analyzing notes.
# ABOUTME: Reports progress, detects missing backlinks and tag issues, stores results.

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery
from app.db.session import task_session
from app.models.job import Job, JobStatus
from app.services.note_parser import parse_note
from app.services.obsidian_client import ObsidianClient


async def _run_scan(job_id: str, target_path: str, parameters: dict | None):
    client = ObsidianClient()
    try:
        files = await client.list_folder(target_path)
        md_files = [f for f in files if f.endswith(".md")]

        async with task_session() as session:
            job = await session.get(Job, job_id)
            if not job:
                return
            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            job.progress_total = len(md_files)
            job.progress_current = 0
            await session.commit()

        scan_results = {
            "total_notes": len(md_files),
            "notes_scanned": 0,
            "issues": [],
        }

        all_notes = {}
        for i, file_path in enumerate(md_files):
            try:
                raw = await client.get_note_raw(file_path)
                note = parse_note(file_path, raw)
                all_notes[file_path] = note
            except Exception:
                scan_results["issues"].append({
                    "type": "read_error",
                    "path": file_path,
                })

            async with task_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.progress_current = i + 1
                    await session.commit()

        # Analyze for issues
        all_note_names = set()
        for fp in all_notes:
            name = fp.rsplit("/", 1)[-1].removesuffix(".md")
            all_note_names.add(name)

        scan_type = (parameters or {}).get("scan_type", "full")

        for fp, note in all_notes.items():
            if scan_type in ("full", "missing_backlinks"):
                for link in note.backlinks:
                    if link not in all_note_names:
                        scan_results["issues"].append({
                            "type": "orphaned_backlink",
                            "path": fp,
                            "target": link,
                        })

            if scan_type in ("full", "tag_issues"):
                if not note.tags:
                    scan_results["issues"].append({
                        "type": "no_tags",
                        "path": fp,
                    })

        scan_results["notes_scanned"] = len(all_notes)

        async with task_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.result = scan_results
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


@celery.task(bind=True, name="vault_scan")
def vault_scan(self, job_id: str, target_path: str, parameters: dict | None = None):
    asyncio.run(_run_scan(job_id, target_path, parameters))
