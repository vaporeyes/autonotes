# ABOUTME: Routes for submitting, querying, and cancelling background jobs.
# ABOUTME: POST /jobs with dedup, GET /jobs/{id} with progress, GET /jobs list, POST cancel.

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import not_found, validation_error
from app.db.session import get_session
from app.models.job import JobType
from app.schemas.job import JobProgress, JobRequest, JobListResponse, JobStatusResponse
from app.services import job_service
from app.tasks.ai_analysis import ai_analysis
from app.tasks.vault_cleanup import vault_cleanup
from app.tasks.vault_health_scan import vault_health_scan
from app.tasks.vault_scan import vault_scan

router = APIRouter(tags=["Jobs"])

_TASK_DISPATCH = {
    JobType.vault_scan: vault_scan,
    JobType.vault_cleanup: vault_cleanup,
    JobType.ai_analysis: ai_analysis,
    JobType.vault_health_scan: vault_health_scan,
}


@router.post("/jobs")
async def create_job(req: JobRequest, session: AsyncSession = Depends(get_session)):
    try:
        jt = JobType(req.job_type)
    except ValueError:
        raise validation_error(f"Unknown job_type: {req.job_type}")

    job, is_new = await job_service.create_job(
        session,
        job_type=req.job_type,
        target_path=req.target_path,
        parameters=req.parameters,
    )
    await session.commit()

    if is_new:
        task_func = _TASK_DISPATCH.get(jt)
        if task_func:
            result = task_func.delay(str(job.id), req.target_path, req.parameters)
            job.celery_task_id = result.id
            await session.commit()

        return JSONResponse(
            status_code=201,
            content={
                "job_id": str(job.id),
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
            },
        )

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": "Identical job already in progress",
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    job = await job_service.get_job(session, job_id)
    if not job:
        raise not_found(f"Job not found: {job_id}")

    progress = None
    if job.progress_total is not None:
        progress = JobProgress(current=job.progress_current, total=job.progress_total)

    return JobStatusResponse(
        job_id=str(job.id),
        job_type=job.job_type.value,
        status=job.status.value,
        progress=progress,
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: str | None = Query(None),
    job_type: str | None = Query(None),
    since: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    jobs, total = await job_service.list_jobs(session, status=status, job_type=job_type, since=since, limit=limit)

    items = [
        JobStatusResponse(
            job_id=str(j.id),
            job_type=j.job_type.value,
            status=j.status.value,
            progress=JobProgress(current=j.progress_current, total=j.progress_total)
            if j.progress_total is not None else None,
            result=j.result,
            error_message=j.error_message,
            created_at=j.created_at,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]

    return JobListResponse(jobs=items, total=total)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    job = await job_service.cancel_job(session, job_id)
    if not job:
        raise not_found(f"Job not found: {job_id}")
    await session.commit()
    return {"status": job.status.value}
