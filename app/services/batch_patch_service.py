# ABOUTME: Service for applying patch operations across multiple notes in batch.
# ABOUTME: Supports folder-based and query-based note selection, dry-run preview, and per-note results.

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.operation_log import LogStatus
from app.models.patch_operation import OperationType, PatchOperation, PatchStatus
from app.schemas.batch_patch import BatchPatchResult, NoteResult
from app.schemas.patch import PatchOperationRequest
from app.services import log_service
from app.services.note_parser import compute_content_hash
from app.services.obsidian_client import ObsidianClient
from app.services.patch_engine import apply_patch, classify_risk, compute_idempotency_key

logger = logging.getLogger(__name__)


async def list_target_notes(
    folder_path: str,
    recursive: bool = False,
) -> list[str]:
    """List markdown notes in a folder, optionally recursive."""
    client = ObsidianClient()
    try:
        files = await client.list_folder(folder_path, recursive=recursive)
    finally:
        await client.close()
    return [f for f in files if f.endswith(".md")]


async def list_target_notes_by_query(
    session: AsyncSession,
    query: str,
    threshold: float = 0.5,
    limit: int | None = None,
) -> list[str]:
    """List notes matching a similarity query."""
    from app.services.similarity_service import search_similar

    result = await search_similar(
        session,
        query=query,
        threshold=threshold,
        limit=limit or 200,
    )
    return [item.note_path for item in result.results]


async def apply_batch(
    session: AsyncSession,
    note_paths: list[str],
    operations: list[PatchOperationRequest],
    dry_run: bool = False,
    job: Job | None = None,
    progress_callback=None,
) -> BatchPatchResult:
    """Apply operations to a list of notes. Returns aggregated results."""
    results: list[NoteResult] = []
    applied_count = 0
    skipped_count = 0
    pending_count = 0
    failed_count = 0
    total = len(note_paths)

    client = ObsidianClient()
    try:
        for idx, note_path in enumerate(note_paths):
            try:
                note_result = await _apply_to_note(
                    session, client, note_path, operations, dry_run, job
                )
                results.append(note_result)

                if note_result.status == "applied":
                    applied_count += 1
                elif note_result.status in ("no_op", "would_skip"):
                    skipped_count += 1
                elif note_result.status == "pending_approval":
                    pending_count += 1
                elif note_result.status == "would_apply":
                    applied_count += 1
                elif note_result.status == "failed":
                    failed_count += 1
            except Exception:
                logger.warning("Failed to process note in batch: %s", note_path)
                results.append(NoteResult(
                    note_path=note_path, status="failed", reason="unexpected error"
                ))
                failed_count += 1

            if progress_callback:
                await progress_callback(idx + 1, total)
    finally:
        await client.close()

    if not dry_run:
        await session.flush()

    return BatchPatchResult(
        job_id=str(job.id) if job else None,
        target_count=total,
        applied_count=applied_count,
        skipped_count=skipped_count,
        pending_count=pending_count,
        failed_count=failed_count,
        dry_run=dry_run,
        results=results,
    )


async def _apply_to_note(
    session: AsyncSession,
    client: ObsidianClient,
    note_path: str,
    operations: list[PatchOperationRequest],
    dry_run: bool,
    job: Job | None,
) -> NoteResult:
    """Apply operations to a single note within a batch."""
    import frontmatter as fm

    try:
        raw_content = await client.get_note_raw(note_path)
    except Exception as exc:
        return NoteResult(note_path=note_path, status="failed", reason=str(exc))

    before_hash = compute_content_hash(raw_content)
    current_content = raw_content
    patch_ids: list[str] = []
    any_changed = False
    any_pending = False

    for op in operations:
        # Capture previous value for undo support
        payload = dict(op.payload)
        if op.type == "update_frontmatter_key" and "previous_value" not in payload:
            try:
                post = fm.loads(current_content)
                payload["previous_value"] = post.metadata.get(payload["key"])
            except Exception:
                pass

        if dry_run:
            _, changed = apply_patch(current_content, op.type, payload)
            if changed:
                any_changed = True
            continue

        risk = classify_risk(op.type)
        idem_key = compute_idempotency_key(note_path, op.type, payload)

        patch_op = PatchOperation(
            job_id=job.id if job else None,
            target_path=note_path,
            operation_type=OperationType(op.type),
            payload=payload,
            idempotency_key=idem_key,
            risk_level=risk,
            before_hash=before_hash,
        )

        if risk.value == "low":
            new_content, changed = apply_patch(current_content, op.type, payload)
            if changed:
                patch_op.status = PatchStatus.applied
                patch_op.after_hash = compute_content_hash(new_content)
                patch_op.applied_at = datetime.now(timezone.utc)
                current_content = new_content
                any_changed = True
            else:
                patch_op.status = PatchStatus.applied
                patch_op.after_hash = before_hash
                patch_op.applied_at = datetime.now(timezone.utc)
        else:
            patch_op.status = PatchStatus.pending_approval
            any_pending = True

        session.add(patch_op)
        await session.flush()
        patch_ids.append(str(patch_op.id))

        await log_service.create_log(
            session,
            operation_name=f"batch:{op.type}",
            target_path=note_path,
            status=LogStatus.success if patch_op.status == PatchStatus.applied else LogStatus.no_op,
            job_id=job.id if job else None,
            patch_operation_id=patch_op.id,
            before_hash=str(patch_op.before_hash),
            after_hash=str(patch_op.after_hash) if patch_op.after_hash else None,
        )

    if dry_run:
        status = "would_apply" if any_changed else "would_skip"
        return NoteResult(note_path=note_path, status=status)

    # Write back modified content if any low-risk ops were applied
    if current_content != raw_content:
        try:
            await client.put_note(note_path, current_content)
        except Exception as exc:
            return NoteResult(
                note_path=note_path, status="failed",
                patch_ids=patch_ids, reason=str(exc)
            )

    if any_pending:
        status = "pending_approval"
    elif any_changed:
        status = "applied"
    else:
        status = "no_op"

    return NoteResult(note_path=note_path, status=status, patch_ids=patch_ids)
