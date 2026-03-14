# ABOUTME: Pydantic schemas for similarity search, duplicate detection, and embedding status.
# ABOUTME: Request/response models for the /similarity and /embeddings API endpoints.

from datetime import datetime

from pydantic import BaseModel, Field


class SimilaritySearchRequest(BaseModel):
    note_path: str | None = None
    query: str | None = None
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    limit: int = Field(default=20, ge=1, le=100)


class SimilarityResultItem(BaseModel):
    note_path: str
    similarity: float
    title: str | None = None
    tags: list[str] = []


class SimilaritySearchResponse(BaseModel):
    source: str
    results: list[SimilarityResultItem]
    total: int
    threshold: float
    embedded_on_the_fly: bool = False


class DuplicatePairResponse(BaseModel):
    note_path_a: str
    note_path_b: str
    similarity: float
    excerpt_a: str = ""
    excerpt_b: str = ""


class DuplicatesResponse(BaseModel):
    job_id: str
    threshold: float
    pairs: list[DuplicatePairResponse]
    total: int


class EmbeddingStatusResponse(BaseModel):
    total_embedded: int
    total_vault_notes: int
    stale_count: int
    last_job_id: str | None = None
    last_embedded_at: datetime | None = None
    model: str
    coverage_percent: float
