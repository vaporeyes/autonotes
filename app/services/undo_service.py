# ABOUTME: Service for undoing applied patch operations via reverse-apply.
# ABOUTME: Supports single-patch undo and batch undo (by job ID) with hash verification.

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import LogStatus
from app.models.patch_operation import PatchOperation, PatchStatus
from app.schemas.undo import BatchUndoResponse, UndoDetail, UndoResponse
from app.services import log_service
from app.services.note_parser import compute_content_hash
from app.services.obsidian_client import ObsidianClient
from app.services.patch_engine import reverse_apply_patch

logger = logging.getLogger(__name__)


async def undo_patch(
    session: AsyncSession,
    patch_id: uuid.UUID,
) -> UndoResponse:
    """Undo a single applied patch operation by reverse-applying it."""
    patch_op = await session.get(PatchOperation, patch_id)
    if not patch_op:
        raise PatchNotFoundError(str(patch_id))

    if patch_op.status != PatchStatus.applied:
        raise PatchNotUndoableError(
            f"Patch is {patch_op.status.value}, not applied"
        )

    client = ObsidianClient()
    try:
        try:
            raw_content = await client.get_note_raw(patch_op.target_path)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NoteDeletedError(patch_op.target_path)
            raise

        current_hash = compute_content_hash(raw_content)
        if current_hash != patch_op.after_hash:
            raise NoteDivergedError(
                patch_op.target_path,
                expected_hash=patch_op.after_hash,
                current_hash=current_hash,
            )

        new_content, changed = reverse_apply_patch(
            raw_content,
            patch_op.operation_type.value,
            patch_op.payload,
        )
        after_hash = compute_content_hash(new_content) if changed else current_hash

        if changed:
            await client.put_note(patch_op.target_path, new_content)

        patch_op.status = PatchStatus.reverted

        await log_service.create_log(
            session,
            operation_name=f"undo:{patch_op.operation_type.value}",
            target_path=patch_op.target_path,
            status=LogStatus.success,
            job_id=patch_op.job_id,
            patch_operation_id=patch_op.id,
            before_hash=current_hash,
            after_hash=after_hash,
        )

        return UndoResponse(
            status="reverted",
            before_hash=current_hash,
            after_hash=after_hash,
        )
    finally:
        await client.close()


async def undo_job_patches(
    session: AsyncSession,
    job_id: uuid.UUID,
) -> BatchUndoResponse:
    """Undo all applied patches from a job."""
    result = await session.execute(
        select(PatchOperation)
        .where(PatchOperation.job_id == job_id)
        .where(PatchOperation.status == PatchStatus.applied)
    )
    patches = list(result.scalars().all())

    if not patches:
        raise NoPatchesToUndoError(str(job_id))

    details: list[UndoDetail] = []
    reverted_count = 0
    conflict_count = 0
    error_count = 0

    client = ObsidianClient()
    try:
        for patch_op in patches:
            try:
                # Read current note
                try:
                    raw_content = await client.get_note_raw(patch_op.target_path)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        details.append(UndoDetail(
                            patch_id=str(patch_op.id),
                            note_path=patch_op.target_path,
                            status="error",
                            reason="Note no longer exists in vault",
                        ))
                        error_count += 1
                        continue
                    raise

                current_hash = compute_content_hash(raw_content)
                if current_hash != patch_op.after_hash:
                    details.append(UndoDetail(
                        patch_id=str(patch_op.id),
                        note_path=patch_op.target_path,
                        status="conflict",
                        reason="Note content changed since patch was applied",
                    ))
                    conflict_count += 1
                    continue

                new_content, changed = reverse_apply_patch(
                    raw_content,
                    patch_op.operation_type.value,
                    patch_op.payload,
                )
                after_hash = compute_content_hash(new_content) if changed else current_hash

                if changed:
                    await client.put_note(patch_op.target_path, new_content)

                patch_op.status = PatchStatus.reverted

                await log_service.create_log(
                    session,
                    operation_name=f"undo:{patch_op.operation_type.value}",
                    target_path=patch_op.target_path,
                    status=LogStatus.success,
                    job_id=patch_op.job_id,
                    patch_operation_id=patch_op.id,
                    before_hash=current_hash,
                    after_hash=after_hash,
                )

                details.append(UndoDetail(
                    patch_id=str(patch_op.id),
                    note_path=patch_op.target_path,
                    status="reverted",
                ))
                reverted_count += 1

            except Exception as exc:
                logger.warning("Failed to undo patch %s: %s", patch_op.id, exc)
                details.append(UndoDetail(
                    patch_id=str(patch_op.id),
                    note_path=patch_op.target_path,
                    status="error",
                    reason=str(exc),
                ))
                error_count += 1
    finally:
        await client.close()

    return BatchUndoResponse(
        job_id=str(job_id),
        reverted_count=reverted_count,
        conflict_count=conflict_count,
        error_count=error_count,
        results=details,
    )


class PatchNotFoundError(Exception):
    pass


class PatchNotUndoableError(Exception):
    pass


class NoteDeletedError(Exception):
    def __init__(self, target_path: str):
        self.target_path = target_path
        super().__init__(f"Note no longer exists: {target_path}")


class NoteDivergedError(Exception):
    def __init__(self, target_path: str, expected_hash: str, current_hash: str):
        self.target_path = target_path
        self.expected_hash = expected_hash
        self.current_hash = current_hash
        super().__init__(f"Note content diverged: {target_path}")


class NoPatchesToUndoError(Exception):
    pass
