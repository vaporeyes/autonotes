# ABOUTME: Routes for batch patch operations across multiple notes.
# ABOUTME: Supports folder-based and query-based selection with sync/async threshold.

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import not_found, obsidian_unreachable
from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.schemas.batch_patch import BatchPatchAsyncResponse, BatchPatchRequest, BatchPatchResult
from app.services.batch_patch_service import (
    apply_batch,
    list_target_notes,
    list_target_notes_by_query,
)

router = APIRouter(tags=["Batch Patches"])

_ASYNC_THRESHOLD = 10


@router.post("/batch-patches")
async def create_batch_patch(
    req: BatchPatchRequest,
    session: AsyncSession = Depends(get_session),
):
    # Resolve target notes
    try:
        if req.folder_path:
            note_paths = await list_target_notes(req.folder_path, recursive=req.recursive)
        else:
            note_paths = await list_target_notes_by_query(
                session, req.query, threshold=req.threshold, limit=req.limit
            )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise not_found(f"Folder not found: {req.folder_path}")
        raise
    except httpx.ConnectError:
        raise obsidian_unreachable()

    if not note_paths:
        return BatchPatchResult(
            target_count=0, dry_run=req.dry_run, results=[]
        )

    # Dry-run or small batch: execute synchronously
    if req.dry_run or len(note_paths) <= _ASYNC_THRESHOLD:
        job = Job(
            job_type=JobType.batch_patch,
            target_path=req.folder_path or f"query:{req.query}",
            status=JobStatus.running,
        )
        if not req.dry_run:
            session.add(job)
            await session.flush()

        result = await apply_batch(
            session, note_paths, req.operations,
            dry_run=req.dry_run,
            job=job if not req.dry_run else None,
        )

        if not req.dry_run:
            job.status = JobStatus.completed
            job.completed_at = datetime.now(timezone.utc)
            job.result = result.model_dump()

        await session.commit()
        return result

    # Large batch: dispatch as async job
    job = Job(
        job_type=JobType.batch_patch,
        target_path=req.folder_path or f"query:{req.query}",
        parameters={
            "folder_path": req.folder_path,
            "query": req.query,
            "threshold": req.threshold,
            "limit": req.limit,
            "recursive": req.recursive,
            "operations": [op.model_dump() for op in req.operations],
        },
        status=JobStatus.pending,
    )
    session.add(job)
    await session.flush()

    from app.tasks.batch_patch_job import batch_patch as batch_patch_task
    celery_result = batch_patch_task.delay(str(job.id), job.target_path, job.parameters)
    job.celery_task_id = celery_result.id
    await session.commit()

    return JSONResponse(
        status_code=202,
        content=BatchPatchAsyncResponse(
            job_id=str(job.id),
            status="pending",
            message=f"Batch operation queued for {len(note_paths)} notes. Monitor progress via GET /jobs/{job.id}.",
        ).model_dump(),
    )
