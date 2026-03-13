# ABOUTME: API routes for vault health analytics (snapshots, trends, dashboard).
# ABOUTME: GET endpoints for retrieving health data; scans are submitted via POST /jobs.

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import not_found, validation_error
from app.config import settings
from app.db.session import get_session
from app.models.health_snapshot import HealthSnapshot
from app.schemas.health import (
    DashboardResponse,
    HealthSnapshotResponse,
    HealthTrendResponse,
    TrendDataPoint,
    TrendSummary,
)
from app.services import health_service

router = APIRouter(prefix="/vault-health", tags=["Vault Health"])


def _snapshot_to_response(snap: HealthSnapshot) -> HealthSnapshotResponse:
    return HealthSnapshotResponse(
        snapshot_id=str(snap.id),
        job_id=str(snap.job_id),
        scan_scope=snap.scan_scope,
        total_notes=snap.total_notes,
        orphan_count=snap.orphan_count,
        orphan_paths=snap.orphan_paths,
        zero_outbound_paths=snap.zero_outbound_paths,
        tag_distribution=snap.tag_distribution,
        unique_tag_count=snap.unique_tag_count,
        backlink_density=snap.backlink_density,
        cluster_count=snap.cluster_count,
        cluster_sizes=snap.cluster_sizes,
        health_score=snap.health_score,
        skipped_notes=snap.skipped_notes,
        created_at=snap.created_at,
    )


@router.get("/snapshot/{job_id}", response_model=HealthSnapshotResponse)
async def get_snapshot_by_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select

    stmt = select(HealthSnapshot).where(HealthSnapshot.job_id == job_id)
    result = await session.execute(stmt)
    snap = result.scalar_one_or_none()
    if not snap:
        raise not_found(f"No snapshot found for job {job_id}")
    return _snapshot_to_response(snap)


@router.get("/latest", response_model=HealthSnapshotResponse)
async def get_latest_snapshot(
    scope: str = Query("/", description="Scan scope (folder path or / for full vault)"),
    session: AsyncSession = Depends(get_session),
):
    snap = await health_service.get_latest_snapshot(session, scope)
    if not snap:
        raise not_found(f"No snapshots exist for scope {scope}")
    return _snapshot_to_response(snap)


@router.get("/trends", response_model=HealthTrendResponse)
async def get_trends(
    metric: str = Query(..., description="Metric name"),
    scope: str = Query("/"),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    if metric not in health_service.TREND_METRICS:
        raise validation_error(
            f"Unknown metric: {metric}. Valid: {', '.join(sorted(health_service.TREND_METRICS))}"
        )

    now = datetime.now(timezone.utc)
    since_dt = since or (now - timedelta(days=30))
    until_dt = until or now

    trend = await health_service.get_trend(session, scope, metric, since_dt, until_dt)

    data_points = [TrendDataPoint(timestamp=dp["timestamp"], value=dp["value"]) for dp in trend["data_points"]]

    message = None
    if not data_points:
        message = "No historical data available"

    return HealthTrendResponse(
        metric=trend["metric"],
        scan_scope=trend["scan_scope"],
        time_range={"start": since_dt, "end": until_dt},
        data_points=data_points,
        delta=trend["delta"],
        avg_7d=trend["avg_7d"],
        avg_30d=trend["avg_30d"],
        message=message,
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    scope: str = Query("/"),
    session: AsyncSession = Depends(get_session),
):
    threshold = settings.health_stale_threshold_hours
    dashboard = await health_service.get_dashboard(session, scope, threshold)

    if dashboard.get("message"):
        return DashboardResponse(message=dashboard["message"])

    latest = dashboard["latest_snapshot"]
    snapshot_resp = _snapshot_to_response(latest)

    trends = {}
    for metric_name, summary in dashboard["trends"].items():
        trends[metric_name] = TrendSummary(
            delta=summary["delta"],
            avg_7d=summary["avg_7d"],
            avg_30d=summary["avg_30d"],
        )

    resp = DashboardResponse(
        latest_snapshot=snapshot_resp,
        stale_data=dashboard["stale_data"],
        stale_threshold_hours=dashboard["stale_threshold_hours"],
        trends=trends,
    )
    if dashboard.get("last_scan_age_hours"):
        resp.last_scan_age_hours = dashboard["last_scan_age_hours"]

    return resp
