# Quickstart: Vault Health Analytics

**Date**: 2026-03-12
**Feature Branch**: `002-vault-health-analytics`

## Prerequisites

- Existing autonotes stack running (`docker compose up -d`)
- Database migrations applied (`docker compose exec api uv run alembic upgrade head`)
- Obsidian vault accessible via Local REST API

## Workflow

### 1. Run a Health Scan

Submit a health scan job via the existing jobs endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type": "vault_health_scan", "target_path": "/"}'
```

Response returns a `job_id`. Monitor progress:

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

### 2. View the Snapshot

Once the job completes, retrieve the full snapshot:

```bash
curl http://localhost:8000/api/v1/vault-health/snapshot/{job_id}
```

Or get the latest snapshot for any scope:

```bash
curl http://localhost:8000/api/v1/vault-health/latest?scope=/
```

### 3. Check the Dashboard

Get current metrics plus 30-day trends in one call:

```bash
curl http://localhost:8000/api/v1/vault-health/dashboard
```

### 4. Query Trends

Get historical orphan count over the last 30 days:

```bash
curl "http://localhost:8000/api/v1/vault-health/trends?metric=orphan_count&since=2026-02-10"
```

Available metrics: `orphan_count`, `backlink_density`, `cluster_count`,
`unique_tag_count`, `health_score`.

### 5. Scoped Scans

Scan a specific folder instead of the full vault:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type": "vault_health_scan", "target_path": "Notes/projects/"}'
```

### 6. Scheduled Scans

Scheduled health scans run automatically via Celery beat (configured in
`celery_app.py`). Default: daily. To change the schedule, update the
`HEALTH_SCAN_CRON` environment variable and restart the worker.

## Verification Checklist

1. Submit a health scan job -- expect 201 with job_id
2. Poll job status -- expect progress updates, then "completed"
3. Retrieve snapshot -- expect all four metrics populated
4. Submit a second scan -- expect different snapshot with timestamps
5. Query dashboard -- expect latest snapshot + trend deltas
6. Query trends for orphan_count -- expect time-series data points
7. Submit duplicate scan while first is running -- expect 200 with
   existing job_id (deduplication)
