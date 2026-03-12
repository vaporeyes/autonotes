# ABOUTME: Pydantic request/response schemas for patch operations.
# ABOUTME: PatchRequest with operations list, PatchResult with per-op status.

from pydantic import BaseModel


class PatchOperationRequest(BaseModel):
    type: str
    payload: dict


class PatchRequest(BaseModel):
    target_path: str
    operations: list[PatchOperationRequest]


class PatchOperationResult(BaseModel):
    type: str
    status: str
    reason: str | None = None


class PatchResult(BaseModel):
    target_path: str
    results: list[PatchOperationResult]
    job_id: str


class ApproveResponse(BaseModel):
    status: str
    after_hash: str | None = None


class RejectResponse(BaseModel):
    status: str
