# API Contract: Vault Health Analytics

**Date**: 2026-03-12
**Feature Branch**: `002-vault-health-analytics`
**Base URL**: `http://localhost:8000/api/v1`

## New Endpoints

All endpoints extend the existing API. Authentication: none (inherits
single-user localhost model from 001).

### Health Scan

#### POST /jobs

Submit a health scan job (uses existing jobs endpoint).

**Request body**:
```json
{
  "job_type": "vault_health_scan",
  "target_path": "Notes/",
  "parameters": {}
}
```

**Response 201** (new job):
```json
{
  "job_id": "uuid-789",
  "status": "pending",
  "created_at": "2026-03-12T14:00:00Z"
}
```

**Response 200** (duplicate detected):
```json
{
  "job_id": "uuid-existing",
  "status": "running",
  "message": "Identical job already in progress"
}
```

Job progress tracked via existing `GET /jobs/{job_id}` endpoint.

### Health Snapshots

#### GET /vault-health/snapshot/{job_id}

Retrieve the health snapshot for a completed scan job.

**Path params**: `job_id` -- UUID of the health scan job

**Response 200**:
```json
{
  "snapshot_id": "uuid-snap-1",
  "job_id": "uuid-789",
  "scan_scope": "Notes/",
  "total_notes": 100,
  "orphan_count": 8,
  "orphan_paths": ["Notes/orphan1.md", "Notes/orphan2.md"],
  "zero_outbound_paths": ["Notes/island.md"],
  "tag_distribution": {"daily": 42, "review": 15, "project": 10},
  "unique_tag_count": 25,
  "backlink_density": 3.2,
  "cluster_count": 2,
  "cluster_sizes": [85, 15],
  "health_score": 72.5,
  "skipped_notes": [],
  "created_at": "2026-03-12T14:01:30Z"
}
```

**Response 404**: `{"detail": "No snapshot found for job uuid-789"}`

#### GET /vault-health/latest

Get the most recent snapshot for a given scope.

**Query params**: `scope` (string, default "/")

**Response 200**: Same shape as snapshot response above.

**Response 404**: `{"detail": "No snapshots exist for scope /"}`

### Historical Trends

#### GET /vault-health/trends

Query historical metric trends.

**Query params**:
- `scope` (string, default "/")
- `metric` (string, required): one of `orphan_count`,
  `backlink_density`, `cluster_count`, `unique_tag_count`, `health_score`
- `since` (datetime, default 30 days ago)
- `until` (datetime, default now)

**Response 200**:
```json
{
  "metric": "orphan_count",
  "scan_scope": "/",
  "time_range": {
    "start": "2026-02-10T00:00:00Z",
    "end": "2026-03-12T23:59:59Z"
  },
  "data_points": [
    {"timestamp": "2026-02-15T08:00:00Z", "value": 12},
    {"timestamp": "2026-02-22T08:00:00Z", "value": 10},
    {"timestamp": "2026-03-01T08:00:00Z", "value": 8}
  ],
  "delta": -2,
  "avg_7d": 8.5,
  "avg_30d": 10.0
}
```

**Response 200** (no data):
```json
{
  "metric": "orphan_count",
  "scan_scope": "/",
  "time_range": {"start": "...", "end": "..."},
  "data_points": [],
  "delta": null,
  "avg_7d": null,
  "avg_30d": null,
  "message": "No historical data available"
}
```

### Dashboard

#### GET /vault-health/dashboard

Consolidated view: latest snapshot + trend summaries.

**Query params**: `scope` (string, default "/")

**Response 200**:
```json
{
  "latest_snapshot": {
    "snapshot_id": "uuid-snap-1",
    "scan_scope": "/",
    "total_notes": 100,
    "orphan_count": 8,
    "backlink_density": 3.2,
    "cluster_count": 2,
    "unique_tag_count": 25,
    "health_score": 72.5,
    "created_at": "2026-03-12T14:01:30Z"
  },
  "stale_data": false,
  "stale_threshold_hours": 24,
  "trends": {
    "orphan_count": {"delta": -2, "avg_7d": 8.5, "avg_30d": 10.0},
    "backlink_density": {"delta": 0.3, "avg_7d": 3.1, "avg_30d": 2.9},
    "cluster_count": {"delta": 0, "avg_7d": 2.0, "avg_30d": 2.2},
    "unique_tag_count": {"delta": 3, "avg_7d": 24.0, "avg_30d": 22.0},
    "health_score": {"delta": 4.2, "avg_7d": 70.1, "avg_30d": 68.3}
  }
}
```

**Response 200** (no data):
```json
{
  "latest_snapshot": null,
  "stale_data": null,
  "trends": null,
  "message": "No health scans have been run. Submit a vault_health_scan job to get started."
}
```

**Response 200** (stale):
```json
{
  "latest_snapshot": {"...": "..."},
  "stale_data": true,
  "stale_threshold_hours": 24,
  "last_scan_age_hours": 36.5,
  "trends": {"...": "..."}
}
```

## Error Format

Follows existing error contract from 001:

```json
{
  "detail": "Human-readable error message",
  "error_code": "NOT_FOUND",
  "context": {}
}
```

Error codes used by this feature: `NOT_FOUND`, `VALIDATION_ERROR`.
