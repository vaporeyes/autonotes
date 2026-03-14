# ABOUTME: Pydantic request/response schemas for batch patch operations.
# ABOUTME: Supports folder-based and query-based batch patching with dry-run preview.

from pydantic import BaseModel, model_validator

from app.schemas.patch import PatchOperationRequest


class BatchPatchRequest(BaseModel):
    folder_path: str | None = None
    query: str | None = None
    threshold: float = 0.5
    limit: int | None = None
    recursive: bool = False
    operations: list[PatchOperationRequest]
    dry_run: bool = False

    @model_validator(mode="after")
    def validate_scope(self):
        if self.folder_path and self.query:
            raise ValueError("Provide exactly one of folder_path or query, not both")
        if not self.folder_path and not self.query:
            raise ValueError("Provide exactly one of folder_path or query")
        return self


class NoteResult(BaseModel):
    note_path: str
    status: str
    patch_ids: list[str] = []
    reason: str | None = None


class BatchPatchResult(BaseModel):
    job_id: str | None = None
    target_count: int
    applied_count: int = 0
    skipped_count: int = 0
    pending_count: int = 0
    failed_count: int = 0
    dry_run: bool = False
    results: list[NoteResult] = []


class BatchPatchAsyncResponse(BaseModel):
    job_id: str
    status: str
    message: str
