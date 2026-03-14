# ABOUTME: Pydantic response schemas for undo/rollback operations.
# ABOUTME: Covers single-patch undo and batch undo (by job ID) responses.

from pydantic import BaseModel


class UndoResponse(BaseModel):
    status: str
    before_hash: str | None = None
    after_hash: str | None = None


class UndoDetail(BaseModel):
    patch_id: str
    note_path: str
    status: str
    reason: str | None = None


class BatchUndoResponse(BaseModel):
    job_id: str
    reverted_count: int = 0
    conflict_count: int = 0
    error_count: int = 0
    results: list[UndoDetail] = []
