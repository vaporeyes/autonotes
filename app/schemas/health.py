# ABOUTME: Pydantic request/response schemas for vault health analytics.
# ABOUTME: Covers snapshots, trends, and dashboard responses.

from datetime import datetime

from pydantic import BaseModel


class HealthSnapshotResponse(BaseModel):
    snapshot_id: str
    job_id: str
    scan_scope: str
    total_notes: int
    orphan_count: int
    orphan_paths: list[str]
    zero_outbound_paths: list[str]
    tag_distribution: dict[str, int]
    unique_tag_count: int
    backlink_density: float
    cluster_count: int
    cluster_sizes: list[int]
    health_score: float
    skipped_notes: list[str]
    created_at: datetime


class TrendDataPoint(BaseModel):
    timestamp: datetime
    value: float


class HealthTrendResponse(BaseModel):
    metric: str
    scan_scope: str
    time_range: dict[str, datetime]
    data_points: list[TrendDataPoint]
    delta: float | None = None
    avg_7d: float | None = None
    avg_30d: float | None = None
    message: str | None = None


class TrendSummary(BaseModel):
    delta: float | None = None
    avg_7d: float | None = None
    avg_30d: float | None = None


class DashboardResponse(BaseModel):
    latest_snapshot: HealthSnapshotResponse | None = None
    stale_data: bool | None = None
    stale_threshold_hours: int | None = None
    last_scan_age_hours: float | None = None
    trends: dict[str, TrendSummary] | None = None
    message: str | None = None
