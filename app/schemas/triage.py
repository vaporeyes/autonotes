# ABOUTME: Pydantic response schemas for triage scan results and history.
# ABOUTME: Defines issue details, scan result summaries, and history listing.

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TriageIssueResponse(BaseModel):
    id: str
    note_path: str
    issue_type: str
    risk_level: str
    suggested_fix: dict[str, Any]
    resolution: str
    patch_operation_id: str | None = None

    model_config = {"from_attributes": True}


class TriageResultResponse(BaseModel):
    job_id: str
    scan_scope: str
    notes_scanned: int
    issues_found: int
    fixes_applied: int
    suggestions_queued: int
    issues: list[TriageIssueResponse]
    created_at: datetime


class TriageScanSummary(BaseModel):
    job_id: str
    scan_scope: str
    notes_scanned: int
    issues_found: int
    fixes_applied: int
    suggestions_queued: int
    created_at: datetime


class TriageHistoryResponse(BaseModel):
    scans: list[TriageScanSummary]
