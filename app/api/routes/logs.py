# ABOUTME: Route for querying operation logs with filtering.
# ABOUTME: GET /logs supports target_path, operation_name, status, date range, and limit.

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.log import LogEntry, LogListResponse
from app.services import log_service

router = APIRouter(tags=["Logs"])


@router.get("/logs", response_model=LogListResponse)
async def get_logs(
    target_path: str | None = Query(None),
    operation_name: str | None = Query(None),
    status: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    logs, total = await log_service.query_logs(
        session,
        target_path=target_path,
        operation_name=operation_name,
        status=status,
        since=since,
        until=until,
        limit=limit,
    )

    entries = [
        LogEntry(
            id=str(log.id),
            job_id=str(log.job_id) if log.job_id else None,
            patch_operation_id=str(log.patch_operation_id) if log.patch_operation_id else None,
            operation_name=log.operation_name,
            target_path=log.target_path,
            before_hash=log.before_hash,
            after_hash=log.after_hash,
            status=log.status.value,
            error_message=log.error_message,
            llm_notes_sent=log.llm_notes_sent,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return LogListResponse(logs=entries, total=total)
