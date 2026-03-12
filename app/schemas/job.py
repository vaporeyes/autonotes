# ABOUTME: Pydantic request/response schemas for background jobs.
# ABOUTME: JobRequest for submission, JobStatus for progress, JobList for filtering.

from datetime import datetime

from pydantic import BaseModel


class JobRequest(BaseModel):
    job_type: str
    target_path: str | None = None
    parameters: dict | None = None


class JobProgress(BaseModel):
    current: int | None
    total: int | None


class JobStatusResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    progress: JobProgress | None = None
    result: dict | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str | None = None


class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]
    total: int
