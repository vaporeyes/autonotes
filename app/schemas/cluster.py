# ABOUTME: Pydantic schemas for note clustering and MOC generation endpoints.
# ABOUTME: Request/response models for the /clusters API endpoints.

from datetime import datetime

from pydantic import BaseModel, Field


class ClusterMemberResponse(BaseModel):
    note_path: str
    similarity_to_centroid: float
    title: str | None = None
    tags: list[str] = []


class ClusterResponse(BaseModel):
    id: str
    job_id: str
    label: str
    note_count: int
    notes: list[ClusterMemberResponse] = []
    created_at: datetime


class ClusterListResponse(BaseModel):
    job_id: str
    created_at: datetime
    clusters: list[ClusterResponse]
    unclustered_count: int
    total_clusters: int


class MOCGenerateRequest(BaseModel):
    target_folder: str = Field(default="30 Maps/")
    title: str | None = None


class MOCDraftResponse(BaseModel):
    patch_id: str
    target_path: str
    preview: str
    note_count: int
    status: str = "pending_approval"
