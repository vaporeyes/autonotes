# Data Model: Vault Health Analytics

**Date**: 2026-03-12
**Feature Branch**: `002-vault-health-analytics`

## Entities

### HealthSnapshot (new table: `health_snapshots`)

A point-in-time record of vault health metrics. Immutable after
creation (read-only analytics, never updated).

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| job_id | uuid | FK to Job that produced this snapshot |
| scan_scope | string | Vault-relative folder path, or "/" for full vault |
| total_notes | int | Total notes scanned |
| orphan_count | int | Notes with zero inbound backlinks |
| orphan_paths | json | List of vault-relative paths of orphan notes |
| zero_outbound_paths | json | List of note paths with zero outbound links |
| tag_distribution | json | Dict of tag -> usage count, sorted by frequency |
| unique_tag_count | int | Count of distinct tags (denormalized for fast queries) |
| backlink_density | float | Average outbound links per note |
| cluster_count | int | Number of disconnected note groups |
| cluster_sizes | json | List of int, one per cluster, sorted descending |
| health_score | float | Composite score 0-100 (weighted formula) |
| skipped_notes | json | List of paths skipped (e.g., deleted mid-scan) |
| created_at | datetime | Snapshot creation timestamp (UTC) |

**Constraints**:
- `job_id` is unique (one snapshot per health scan job)
- `scan_scope` + `created_at` indexed for trend queries
- `created_at` indexed for retention purge

### HealthTrend (derived, not persisted)

Computed on-the-fly from HealthSnapshot queries. Not a database table.

| Field | Type | Description |
|-------|------|-------------|
| metric_name | string | One of: orphan_count, backlink_density, cluster_count, unique_tag_count, health_score |
| scan_scope | string | Scope filter applied |
| time_range | object | {start: datetime, end: datetime} |
| data_points | list | [{timestamp, value}, ...] ordered by timestamp |
| delta | float | Change from second-most-recent to most-recent snapshot |
| avg_7d | float | Rolling 7-day average (null if fewer than 2 snapshots) |
| avg_30d | float | Rolling 30-day average (null if fewer than 2 snapshots) |

### Job (existing table: modified)

**Modification**: Add `vault_health_scan` to the `job_type` enum.

The existing Job model handles all lifecycle tracking (pending, running,
completed, failed, progress_current, progress_total). Health scan jobs
use the same fields:
- `target_path`: scan scope (folder or "/")
- `parameters`: `{"scan_type": "vault_health"}`
- `idempotency_key`: hash of (target_path + "vault_health_scan")
- `result`: summary metrics (redundant with snapshot, kept for job API consistency)

## Relationships

```
Job 1--1 HealthSnapshot   (each health scan job produces one snapshot)
```

HealthSnapshot references the existing Job table via `job_id` FK. No
other cross-table relationships. The feature is self-contained.

## Indexes

- `health_snapshots.job_id` -- unique index (one snapshot per job)
- `health_snapshots.scan_scope, created_at` -- composite index for
  trend queries filtered by scope and date range
- `health_snapshots.created_at` -- for retention purge queries

## Migration Notes

- Add `vault_health_scan` value to the existing `job_type_enum` type
  via `ALTER TYPE job_type_enum ADD VALUE 'vault_health_scan'`
- Create `health_snapshots` table with all fields above
- Both operations in a single Alembic migration using raw SQL (matching
  the pattern from the initial schema migration)
