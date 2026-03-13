# ABOUTME: Vault health analytics service computing structural metrics from parsed notes.
# ABOUTME: Implements Union-Find for cluster detection, metric normalization, and composite scoring.

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_snapshot import HealthSnapshot
from app.services.note_parser import parse_note
from app.services.obsidian_client import ObsidianClient


# -- Union-Find for cluster connectivity (FR-003) --

class UnionFind:
    """Disjoint set with path compression and union by rank."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def add(self, x: str) -> None:
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0

    def find(self, x: str) -> str:
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: str, y: str) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1

    def clusters(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for x in self._parent:
            groups[self.find(x)].append(x)
        return dict(groups)


# -- Metric computation --

def compute_metrics(notes: dict[str, object]) -> dict:
    """Compute all health metrics from a dict of {path: Note}.

    Returns a dict with all fields needed for a HealthSnapshot.
    """
    total = len(notes)
    if total == 0:
        return {
            "total_notes": 0,
            "orphan_count": 0,
            "orphan_paths": [],
            "zero_outbound_paths": [],
            "tag_distribution": {},
            "unique_tag_count": 0,
            "backlink_density": 0.0,
            "cluster_count": 0,
            "cluster_sizes": [],
            "health_score": 0.0,
        }

    # Build name-to-path lookup for inbound link detection
    name_to_path: dict[str, str] = {}
    for path in notes:
        name = path.rsplit("/", 1)[-1].removesuffix(".md")
        name_to_path[name] = path

    # Inbound link counts (for orphan detection)
    inbound_counts: dict[str, int] = defaultdict(int)
    for path, note in notes.items():
        for link in note.backlinks:
            target_path = name_to_path.get(link)
            if target_path:
                inbound_counts[target_path] += 1

    # Orphan notes: zero inbound backlinks
    orphan_paths = sorted(p for p in notes if inbound_counts.get(p, 0) == 0)

    # Notes with zero outbound links
    zero_outbound = sorted(p for p, n in notes.items() if len(n.backlinks) == 0)

    # Tag distribution
    tag_counts: dict[str, int] = defaultdict(int)
    for note in notes.values():
        for tag in note.tags:
            tag_counts[tag] += 1
    tag_distribution = dict(sorted(tag_counts.items(), key=lambda kv: -kv[1]))

    # Backlink density: average outbound links per note
    total_outbound = sum(len(n.backlinks) for n in notes.values())
    density = total_outbound / total

    # Cluster connectivity via Union-Find (bidirectional edges)
    uf = UnionFind()
    for path in notes:
        uf.add(path)
    for path, note in notes.items():
        for link in note.backlinks:
            target = name_to_path.get(link)
            if target:
                uf.union(path, target)

    cluster_groups = uf.clusters()
    cluster_sizes = sorted((len(members) for members in cluster_groups.values()), reverse=True)

    # Composite health score (FR-010)
    score = compute_health_score(
        orphan_count=len(orphan_paths),
        total_notes=total,
        backlink_density=density,
        cluster_count=len(cluster_sizes),
        unique_tag_count=len(tag_counts),
    )

    return {
        "total_notes": total,
        "orphan_count": len(orphan_paths),
        "orphan_paths": orphan_paths,
        "zero_outbound_paths": zero_outbound,
        "tag_distribution": tag_distribution,
        "unique_tag_count": len(tag_counts),
        "backlink_density": round(density, 2),
        "cluster_count": len(cluster_sizes),
        "cluster_sizes": cluster_sizes,
        "health_score": round(score, 1),
    }


def compute_health_score(
    orphan_count: int,
    total_notes: int,
    backlink_density: float,
    cluster_count: int,
    unique_tag_count: int,
) -> float:
    """Weighted composite score 0-100 per clarified formula.

    Weights: orphan ratio 30%, backlink density 30%,
    cluster connectivity 25%, tag distribution 15%.
    Each sub-metric normalized to 0-100 before weighting.
    """
    if total_notes == 0:
        return 0.0

    orphan_score = 100.0 * (1.0 - orphan_count / total_notes)
    density_score = min(100.0, backlink_density * 20.0)
    connectivity_score = 100.0 * (1.0 / cluster_count) if cluster_count > 0 else 0.0
    tag_score = min(100.0, unique_tag_count / total_notes * 200.0)

    return (
        orphan_score * 0.30
        + density_score * 0.30
        + connectivity_score * 0.25
        + tag_score * 0.15
    )


# -- Scan orchestrator (US1) --

async def run_health_scan(
    scope: str,
    client: ObsidianClient,
    progress_callback=None,
) -> dict:
    """Iterate notes in scope, parse each, compute all metrics.

    Args:
        scope: folder path or "/" for full vault
        client: ObsidianClient instance
        progress_callback: optional async callable(current, total) for progress updates

    Returns dict with all HealthSnapshot fields (minus id, job_id, created_at).
    """
    folder = scope.rstrip("/") if scope != "/" else ""
    files = await client.list_folder(folder, recursive=True) if folder else await client.list_folder("", recursive=True)
    md_files = [f for f in files if f.endswith(".md")]

    if progress_callback:
        await progress_callback(0, len(md_files))

    all_notes = {}
    skipped = []
    for i, file_path in enumerate(md_files):
        try:
            raw = await client.get_note_raw(file_path)
            note = parse_note(file_path, raw)
            all_notes[file_path] = note
        except Exception:
            skipped.append(file_path)

        if progress_callback:
            await progress_callback(i + 1, len(md_files))

    metrics = compute_metrics(all_notes)
    metrics["scan_scope"] = scope
    metrics["skipped_notes"] = skipped
    return metrics


# -- Trend queries (US2) --

TREND_METRICS = {
    "orphan_count",
    "backlink_density",
    "cluster_count",
    "unique_tag_count",
    "health_score",
}


async def get_trend(
    session: AsyncSession,
    scope: str,
    metric: str,
    since: datetime,
    until: datetime,
) -> dict:
    """Query historical snapshots and compute trend data for a single metric."""
    stmt = (
        select(HealthSnapshot)
        .where(HealthSnapshot.scan_scope == scope)
        .where(HealthSnapshot.created_at >= since)
        .where(HealthSnapshot.created_at <= until)
        .order_by(HealthSnapshot.created_at)
    )
    result = await session.execute(stmt)
    snapshots = list(result.scalars().all())

    data_points = []
    for s in snapshots:
        value = getattr(s, metric, None)
        if value is not None:
            data_points.append({"timestamp": s.created_at, "value": float(value)})

    delta = None
    if len(data_points) >= 2:
        delta = round(data_points[-1]["value"] - data_points[-2]["value"], 2)

    now = until
    avg_7d = _rolling_average(data_points, now, days=7)
    avg_30d = _rolling_average(data_points, now, days=30)

    return {
        "metric": metric,
        "scan_scope": scope,
        "time_range": {"start": since, "end": until},
        "data_points": data_points,
        "delta": delta,
        "avg_7d": avg_7d,
        "avg_30d": avg_30d,
    }


def _rolling_average(data_points: list[dict], now: datetime, days: int) -> float | None:
    cutoff = now - timedelta(days=days)
    values = [dp["value"] for dp in data_points if dp["timestamp"] >= cutoff]
    if len(values) < 2:
        return None
    return round(sum(values) / len(values), 2)


# -- Dashboard aggregation (US3) --

async def get_latest_snapshot(session: AsyncSession, scope: str) -> HealthSnapshot | None:
    stmt = (
        select(HealthSnapshot)
        .where(HealthSnapshot.scan_scope == scope)
        .order_by(HealthSnapshot.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_dashboard(session: AsyncSession, scope: str, stale_threshold_hours: int) -> dict:
    """Build dashboard combining latest snapshot with trend summaries."""
    latest = await get_latest_snapshot(session, scope)

    if not latest:
        return {
            "latest_snapshot": None,
            "stale_data": None,
            "trends": None,
            "message": "No health scans have been run. Submit a vault_health_scan job to get started.",
        }

    now = datetime.now(timezone.utc)
    age_hours = (now - latest.created_at).total_seconds() / 3600.0
    is_stale = age_hours > stale_threshold_hours

    since_30d = now - timedelta(days=30)
    trends = {}
    for metric in TREND_METRICS:
        trend = await get_trend(session, scope, metric, since_30d, now)
        trends[metric] = {
            "delta": trend["delta"],
            "avg_7d": trend["avg_7d"],
            "avg_30d": trend["avg_30d"],
        }

    result = {
        "latest_snapshot": latest,
        "stale_data": is_stale,
        "stale_threshold_hours": stale_threshold_hours,
        "trends": trends,
    }
    if is_stale:
        result["last_scan_age_hours"] = round(age_hours, 1)

    return result


# -- Snapshot purge (US4) --

async def purge_old_snapshots(session: AsyncSession, retention_days: int = 365) -> int:
    """Delete snapshots older than retention_days. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    stmt = select(HealthSnapshot).where(HealthSnapshot.created_at < cutoff)
    result = await session.execute(stmt)
    old_snapshots = list(result.scalars().all())
    for snap in old_snapshots:
        await session.delete(snap)
    if old_snapshots:
        await session.commit()
    return len(old_snapshots)
