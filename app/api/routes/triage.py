# ABOUTME: Routes for viewing triage scan results and history.
# ABOUTME: GET /triage/results/{job_id} for detailed issues, GET /triage/history for summaries.

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import not_found
from app.db.session import get_session
from app.models.job import Job, JobType
from app.models.triage_issue import TriageIssue
from app.schemas.triage import (
    TriageHistoryResponse,
    TriageIssueResponse,
    TriageResultResponse,
    TriageScanSummary,
)

router = APIRouter(tags=["Triage"])


@router.get("/triage/results/{job_id}", response_model=TriageResultResponse)
async def get_triage_results(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    job = await session.get(Job, job_id)
    if not job or job.job_type != JobType.triage_scan:
        raise not_found(f"No triage results found for job {job_id}")

    result = await session.execute(
        select(TriageIssue).where(TriageIssue.job_id == job_id).order_by(TriageIssue.created_at)
    )
    issues = list(result.scalars().all())

    job_result = job.result or {}
    return TriageResultResponse(
        job_id=str(job.id),
        scan_scope=job.target_path or "/",
        notes_scanned=job_result.get("notes_scanned", 0),
        issues_found=job_result.get("issues_found", 0),
        fixes_applied=job_result.get("fixes_applied", 0),
        suggestions_queued=job_result.get("suggestions_queued", 0),
        issues=[
            TriageIssueResponse(
                id=str(issue.id),
                note_path=issue.note_path,
                issue_type=issue.issue_type.value,
                risk_level=issue.risk_level,
                suggested_fix=issue.suggested_fix,
                resolution=issue.resolution.value,
                patch_operation_id=str(issue.patch_operation_id) if issue.patch_operation_id else None,
            )
            for issue in issues
        ],
        created_at=job.created_at,
    )


@router.get("/triage/history", response_model=TriageHistoryResponse)
async def get_triage_history(
    scope: str | None = Query(None),
    since: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)

    query = (
        select(Job)
        .where(Job.job_type == JobType.triage_scan, Job.created_at >= since)
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    if scope:
        query = query.where(Job.target_path == scope)

    result = await session.execute(query)
    jobs = list(result.scalars().all())

    scans = []
    for job in jobs:
        job_result = job.result or {}
        scans.append(TriageScanSummary(
            job_id=str(job.id),
            scan_scope=job.target_path or "/",
            notes_scanned=job_result.get("notes_scanned", 0),
            issues_found=job_result.get("issues_found", 0),
            fixes_applied=job_result.get("fixes_applied", 0),
            suggestions_queued=job_result.get("suggestions_queued", 0),
            created_at=job.created_at,
        ))

    return TriageHistoryResponse(scans=scans)
