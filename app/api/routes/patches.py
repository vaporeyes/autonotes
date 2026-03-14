# ABOUTME: Routes for submitting, approving, and rejecting patch operations.
# ABOUTME: POST /patches creates a job with per-op risk classification and idempotency.

import uuid
from datetime import datetime, timezone

import frontmatter as fm
import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import conflict, not_found, obsidian_error, obsidian_unreachable
from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.models.operation_log import LogStatus
from app.models.patch_operation import OperationType, PatchOperation, PatchStatus
from app.schemas.patch import (
    ApproveResponse,
    PatchListItem,
    PatchListResponse,
    PatchOperationResult,
    PatchRequest,
    PatchResult,
    RejectResponse,
)
from app.schemas.undo import UndoResponse
from app.services import log_service
from app.services.note_parser import compute_content_hash
from app.services.obsidian_client import obsidian_client
from app.services.patch_engine import apply_patch, classify_risk, compute_idempotency_key

router = APIRouter(tags=["Patches"])


@router.get("/patches", response_model=PatchListResponse)
async def list_patches(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(PatchOperation).order_by(PatchOperation.created_at.desc())
    count_stmt = select(func.count()).select_from(PatchOperation)

    if status:
        try:
            ps = PatchStatus(status)
        except ValueError:
            raise conflict(f"Invalid status: {status}")
        stmt = stmt.where(PatchOperation.status == ps)
        count_stmt = count_stmt.where(PatchOperation.status == ps)

    total = await session.scalar(count_stmt) or 0
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    patches = result.scalars().all()

    items = [
        PatchListItem(
            patch_id=str(p.id),
            job_id=str(p.job_id),
            target_path=p.target_path,
            operation_type=p.operation_type.value,
            payload=p.payload,
            status=p.status.value,
            risk_level=p.risk_level.value,
            created_at=p.created_at.isoformat(),
            applied_at=p.applied_at.isoformat() if p.applied_at else None,
        )
        for p in patches
    ]
    return PatchListResponse(patches=items, total=total)


@router.post("/patches", response_model=PatchResult)
async def create_patches(req: PatchRequest, session: AsyncSession = Depends(get_session)):
    # Fetch current note content
    try:
        raw_content = await obsidian_client.get_note_raw(req.target_path)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise not_found(f"Note not found: {req.target_path}", target_path=req.target_path)
        raise obsidian_error(str(exc), target_path=req.target_path)
    except httpx.ConnectError:
        raise obsidian_unreachable()

    before_hash = compute_content_hash(raw_content)

    job = Job(job_type=JobType.manual_patch, target_path=req.target_path, status=JobStatus.running)
    session.add(job)
    await session.flush()

    results: list[PatchOperationResult] = []
    current_content = raw_content

    for op in req.operations:
        risk = classify_risk(op.type)

        # Capture previous value for undo support on frontmatter key updates
        if op.type == "update_frontmatter_key" and "previous_value" not in op.payload:
            post = fm.loads(current_content)
            op.payload["previous_value"] = post.metadata.get(op.payload["key"])

        idem_key = compute_idempotency_key(req.target_path, op.type, op.payload)

        # Check for existing idempotent operation
        existing = await session.scalar(
            select(PatchOperation).where(PatchOperation.idempotency_key == idem_key)
        )
        if existing and existing.status == PatchStatus.applied:
            results.append(PatchOperationResult(type=op.type, status="applied", reason="already applied"))
            continue

        patch_op = PatchOperation(
            job_id=job.id,
            target_path=req.target_path,
            operation_type=OperationType(op.type),
            payload=op.payload,
            idempotency_key=idem_key,
            risk_level=risk,
            before_hash=before_hash,
        )

        if risk.value == "low":
            new_content, changed = apply_patch(current_content, op.type, op.payload)
            if changed:
                patch_op.status = PatchStatus.applied
                patch_op.after_hash = compute_content_hash(new_content)
                patch_op.applied_at = datetime.now(timezone.utc)
                current_content = new_content
                results.append(PatchOperationResult(type=op.type, status="applied"))
            else:
                patch_op.status = PatchStatus.applied
                patch_op.after_hash = before_hash
                patch_op.applied_at = datetime.now(timezone.utc)
                results.append(PatchOperationResult(type=op.type, status="applied", reason="no-op"))
        else:
            patch_op.status = PatchStatus.pending_approval
            results.append(PatchOperationResult(
                type=op.type, status="pending_approval",
                reason="high-risk operation requires approval",
            ))

        session.add(patch_op)
        await session.flush()

        await log_service.create_log(
            session,
            operation_name=f"{op.type}:{list(op.payload.values())[0] if op.payload else ''}",
            target_path=req.target_path,
            status=LogStatus.success if patch_op.status == PatchStatus.applied else LogStatus.no_op,
            job_id=job.id,
            patch_operation_id=patch_op.id,
            before_hash=str(patch_op.before_hash),
            after_hash=str(patch_op.after_hash) if patch_op.after_hash else None,
        )

    # Write back modified content if any low-risk ops were applied
    if current_content != raw_content:
        try:
            await obsidian_client.put_note(req.target_path, current_content)
        except httpx.ConnectError:
            raise obsidian_unreachable()

    job.status = JobStatus.completed
    job.completed_at = datetime.now(timezone.utc)
    await session.commit()

    return PatchResult(target_path=req.target_path, results=results, job_id=str(job.id))


@router.post("/patches/{patch_id}/approve", response_model=ApproveResponse)
async def approve_patch(patch_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    patch_op = await session.get(PatchOperation, patch_id)
    if not patch_op:
        raise not_found(f"Patch not found: {patch_id}")
    if patch_op.status != PatchStatus.pending_approval:
        raise conflict(f"Patch is not pending approval: {patch_op.status.value}")

    # Re-read note and verify content hash
    try:
        raw_content = await obsidian_client.get_note_raw(patch_op.target_path)
    except httpx.ConnectError:
        raise obsidian_unreachable()

    current_hash = compute_content_hash(raw_content)
    if current_hash != patch_op.before_hash:
        raise conflict(
            "Note content changed since patch was created",
            target_path=patch_op.target_path,
            expected_hash=patch_op.before_hash,
            current_hash=current_hash,
        )

    new_content, changed = apply_patch(raw_content, patch_op.operation_type.value, patch_op.payload)
    after_hash = compute_content_hash(new_content) if changed else current_hash

    if changed:
        try:
            await obsidian_client.put_note(patch_op.target_path, new_content)
        except httpx.ConnectError:
            raise obsidian_unreachable()

    patch_op.status = PatchStatus.applied
    patch_op.after_hash = after_hash
    patch_op.applied_at = datetime.now(timezone.utc)

    await log_service.create_log(
        session,
        operation_name=f"approve:{patch_op.operation_type.value}",
        target_path=patch_op.target_path,
        status=LogStatus.success,
        job_id=patch_op.job_id,
        patch_operation_id=patch_op.id,
        before_hash=patch_op.before_hash,
        after_hash=after_hash,
    )
    await session.commit()

    return ApproveResponse(status="applied", after_hash=after_hash)


@router.post("/patches/{patch_id}/reject", response_model=RejectResponse)
async def reject_patch(patch_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    patch_op = await session.get(PatchOperation, patch_id)
    if not patch_op:
        raise not_found(f"Patch not found: {patch_id}")
    if patch_op.status != PatchStatus.pending_approval:
        raise conflict(f"Patch is not pending approval: {patch_op.status.value}")

    patch_op.status = PatchStatus.skipped

    await log_service.create_log(
        session,
        operation_name=f"reject:{patch_op.operation_type.value}",
        target_path=patch_op.target_path,
        status=LogStatus.no_op,
        job_id=patch_op.job_id,
        patch_operation_id=patch_op.id,
    )
    await session.commit()

    return RejectResponse(status="skipped")


@router.post("/patches/{patch_id}/undo", response_model=UndoResponse)
async def undo_patch(patch_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    from app.services.undo_service import (
        NoteDivergedError,
        NoteDeletedError,
        PatchNotFoundError,
        PatchNotUndoableError,
        undo_patch as do_undo,
    )
    try:
        result = await do_undo(session, patch_id)
    except PatchNotFoundError:
        raise not_found(f"Patch not found: {patch_id}")
    except PatchNotUndoableError as exc:
        raise conflict(str(exc))
    except NoteDeletedError as exc:
        raise conflict(
            "Note no longer exists in vault",
            target_path=exc.target_path,
        )
    except NoteDivergedError as exc:
        raise conflict(
            "Note content changed since patch was applied",
            target_path=exc.target_path,
            expected_hash=exc.expected_hash,
            current_hash=exc.current_hash,
        )

    await session.commit()
    return result
