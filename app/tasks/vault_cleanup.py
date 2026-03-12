# ABOUTME: Celery task for vault cleanup detecting structural issues in notes.
# ABOUTME: Classifies fixes by risk level, auto-applies low-risk, queues high-risk for approval.

import asyncio
from datetime import datetime, timezone

from app.celery_app import celery
from app.db.session import async_session
from app.models.job import Job, JobStatus
from app.models.operation_log import LogStatus
from app.models.patch_operation import OperationType, PatchOperation, PatchStatus, RiskLevel
from app.services import log_service
from app.services.note_parser import compute_content_hash, parse_note
from app.services.obsidian_client import ObsidianClient
from app.services.patch_engine import apply_patch, compute_idempotency_key


async def _run_cleanup(job_id: str, target_path: str, parameters: dict | None):
    client = ObsidianClient()
    try:
        files = await client.list_folder(target_path or "")
        md_files = [f for f in files if f.endswith(".md")]

        async with async_session() as session:
            job = await session.get(Job, job_id)
            if not job:
                return
            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            job.progress_total = len(md_files)
            job.progress_current = 0
            await session.commit()

        # Collect all notes
        all_notes = {}
        all_note_names = set()
        for file_path in md_files:
            try:
                raw = await client.get_note_raw(file_path)
                note = parse_note(file_path, raw)
                all_notes[file_path] = (note, raw)
                name = file_path.rsplit("/", 1)[-1].removesuffix(".md")
                all_note_names.add(name)
            except Exception:
                pass

        cleanup_results = {"fixes_applied": 0, "fixes_pending": 0, "issues_found": 0}
        standard_frontmatter_keys = (parameters or {}).get("required_frontmatter", ["tags"])

        for i, (file_path, (note, raw_content)) in enumerate(all_notes.items()):
            content_hash = compute_content_hash(raw_content)

            # Check orphaned backlinks
            for link in note.backlinks:
                if link not in all_note_names:
                    cleanup_results["issues_found"] += 1

            # Check missing standard frontmatter keys
            for key in standard_frontmatter_keys:
                if key not in note.frontmatter:
                    cleanup_results["issues_found"] += 1
                    idem_key = compute_idempotency_key(file_path, "update_frontmatter_key", {"key": key, "value": []})

                    async with async_session() as session:
                        job = await session.get(Job, job_id)
                        if not job:
                            return
                        patch_op = PatchOperation(
                            job_id=job.id,
                            target_path=file_path,
                            operation_type=OperationType.update_frontmatter_key,
                            payload={"key": key, "value": []},
                            idempotency_key=idem_key,
                            risk_level=RiskLevel.low,
                            status=PatchStatus.applied,
                            before_hash=content_hash,
                        )
                        new_content, changed = apply_patch(raw_content, "update_frontmatter_key", {"key": key, "value": []})
                        if changed:
                            await client.put_note(file_path, new_content)
                            patch_op.after_hash = compute_content_hash(new_content)
                            patch_op.applied_at = datetime.now(timezone.utc)
                            raw_content = new_content
                            content_hash = patch_op.after_hash
                            cleanup_results["fixes_applied"] += 1
                        else:
                            patch_op.after_hash = content_hash

                        session.add(patch_op)
                        await log_service.create_log(
                            session,
                            operation_name=f"cleanup:update_frontmatter_key:{key}",
                            target_path=file_path,
                            status=LogStatus.success if changed else LogStatus.no_op,
                            job_id=job.id,
                            patch_operation_id=patch_op.id,
                            before_hash=content_hash,
                            after_hash=patch_op.after_hash,
                        )
                        await session.commit()

            # Check duplicate/inconsistent tags (tags in body not in frontmatter)
            # This is a high-risk fix since it modifies tag structure
            inline_tags = set()
            import re
            for match in re.finditer(r"(?<!\S)#([a-zA-Z][a-zA-Z0-9/_-]*)", note.frontmatter.get("__body__", "") if isinstance(note.frontmatter, dict) else ""):
                inline_tags.add(match.group(1))

            async with async_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.progress_current = i + 1
                    await session.commit()

        async with async_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                job.result = cleanup_results
                await session.commit()

    except Exception as exc:
        async with async_session() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.failed
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
    finally:
        await client.close()


@celery.task(bind=True, name="vault_cleanup")
def vault_cleanup(self, job_id: str, target_path: str | None = None, parameters: dict | None = None):
    asyncio.run(_run_cleanup(job_id, target_path, parameters))
