# ABOUTME: Pydantic response schemas for operation log queries.
# ABOUTME: LogEntry for individual logs, LogListResponse for paginated results.

from datetime import datetime

from pydantic import BaseModel


class LogEntry(BaseModel):
    id: str
    job_id: str | None
    patch_operation_id: str | None
    operation_name: str
    target_path: str
    before_hash: str | None
    after_hash: str | None
    status: str
    error_message: str | None
    llm_notes_sent: list[str] | None
    created_at: datetime


class LogListResponse(BaseModel):
    logs: list[LogEntry]
    total: int
