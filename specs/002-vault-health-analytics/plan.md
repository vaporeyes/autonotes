# Implementation Plan: Vault Health Analytics

**Branch**: `002-vault-health-analytics` | **Date**: 2026-03-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-vault-health-analytics/spec.md`

## Summary

Add vault health analytics to the existing AI Orchestrator. The system
computes four structural metrics (orphan notes, tag distribution,
backlink density, cluster connectivity) and a weighted composite score,
persists results as timestamped snapshots in PostgreSQL, serves a
dashboard endpoint combining current metrics with historical trends,
and integrates with the existing Celery job system for scheduled scans.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Celery, httpx, SQLAlchemy, Alembic (all existing)
**Storage**: PostgreSQL 16 (new `health_snapshots` table), Redis 7 (broker)
**Testing**: pytest + pytest-asyncio + httpx test client
**Target Platform**: Docker Compose (existing stack)
**Project Type**: web-service (extension of existing API)
**Performance Goals**: <60s scan for 1000 notes, <2s dashboard, <1s trend query
**Constraints**: Read-only vault access (no writes), single vault, single user
**Scale/Scope**: Vaults up to ~5000 notes, 365 days snapshot retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How Addressed |
|-----------|--------|---------------|
| I. Data Integrity | PASS | Health analytics is read-only (no vault writes). Snapshots are immutable records in PostgreSQL. No note content is modified. |
| II. Surgical Updates | N/A | This feature performs no vault writes. All data flows are read-only: parse notes, compute metrics, store snapshot. |
| III. Local-First Privacy | PASS | All metric computation happens locally. No note content is sent to external services. Snapshots store aggregate metrics and note paths, not note content. |
| IV. Extensibility | PASS | New `vault_health_scan` job type registers via existing enum extension pattern. Health analytics service is a self-contained module. Dashboard endpoint is a new route module. |
| V. Idempotency | PASS | SC-003: same scan on unchanged vault produces identical metrics. Snapshot deduplication via job system's existing idempotency_key mechanism. |

**Post-Phase 1 re-check**: All principles remain satisfied. The feature
is purely additive (new tables, new service module, new routes) with no
modifications to existing write paths.

## Project Structure

### Documentation (this feature)

```text
specs/002-vault-health-analytics/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
app/
├── models/
│   ├── job.py               # MODIFY: add vault_health_scan to JobType enum
│   └── health_snapshot.py   # NEW: HealthSnapshot SQLAlchemy model
├── schemas/
│   └── health.py            # NEW: Health request/response Pydantic schemas
├── services/
│   └── health_service.py    # NEW: Metric computation, graph analysis, scoring
├── tasks/
│   └── vault_health_scan.py # NEW: Celery task for background health scans
├── api/routes/
│   └── vault_health.py      # NEW: Health scan, trends, dashboard endpoints
├── celery_app.py            # MODIFY: add vault_health_scan to include list
└── db/
    └── migrations/          # NEW: migration for health_snapshots table

tests/
├── unit/
│   ├── test_health_service.py    # Metric computation, graph, scoring
│   └── test_health_score.py      # Composite score formula
└── integration/
    └── test_health_endpoints.py  # API contract tests
```

**Structure Decision**: Extension of existing single-project layout.
Three new files (model, service, routes) plus one Celery task. Two
existing files modified (job model enum, celery includes). No new
packages or structural changes.

## Complexity Tracking

No complexity violations. The feature adds one new table, one service
module, one route module, and one Celery task -- all following
established patterns from 001.
