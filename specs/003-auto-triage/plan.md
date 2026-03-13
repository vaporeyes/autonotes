# Implementation Plan: Auto-Triage for Vault Notes

**Branch**: `003-auto-triage` | **Date**: 2026-03-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-auto-triage/spec.md`

## Summary

Build an auto-triage system that compares notes against folder-level
conventions (required frontmatter, expected tags, backlink targets) and
automatically fixes low-risk deviations while queuing high-risk changes
for approval. Reuses the existing patch system, approval workflow, and
job infrastructure.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Celery, SQLAlchemy, Alembic, httpx, python-frontmatter, markdown-it-py
**Storage**: PostgreSQL 16 (conventions, triage issues, scan results), Redis 7 (Celery broker)
**Testing**: pytest
**Target Platform**: Linux server (Docker Compose)
**Project Type**: Web service (API backend)
**Performance Goals**: 500 notes triaged within 60 seconds
**Constraints**: Single-user, single-vault, local-first
**Scale/Scope**: Hundreds to low thousands of notes per vault

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Data Integrity | Pass | Auto-applied patches use existing patch engine which records before_hash. Content hash verified before application (FR-011). |
| II. Surgical Updates | Pass | All fixes go through patch_engine.py which uses key-level merge for frontmatter and targeted ops for body. No full-file rewrites. |
| III. Local-First Privacy | Pass | No LLM involved. All triage logic is rule-based (convention matching). No note content leaves the local environment. |
| IV. Extensibility | Pass | Conventions stored as data (DB rows), not code. New convention rules are added via API, not code changes. |
| V. Idempotency | Pass | Patch engine already enforces idempotency (check-before-write). Duplicate triage scans deduplicated via existing job system. |
| Backup granularity | Pass | Batch operations (multiple auto-applied patches) go through patch_engine which logs before_hash per operation. |
| Conflict resolution | Pass | Content hash check (FR-011) detects concurrent modifications and aborts. |
| Vault boundaries | Pass | Scoped to single vault via existing Obsidian client. |

No violations. Gate passed.

## Project Structure

### Documentation (this feature)

```text
specs/003-auto-triage/
  plan.md              # This file
  research.md          # Phase 0 output
  data-model.md        # Phase 1 output
  quickstart.md        # Phase 1 output
  contracts/           # Phase 1 output
  tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
app/
  models/
    folder_convention.py   # New: FolderConvention ORM model
    triage_issue.py        # New: TriageIssue ORM model
    job.py                 # Modified: add triage_scan to JobType enum
  schemas/
    convention.py          # New: Pydantic request/response schemas
    triage.py              # New: Triage scan result schemas
  services/
    convention_service.py  # New: CRUD + inheritance resolution
    triage_service.py      # New: scan engine, issue detection, fix dispatch
  tasks/
    triage_scan.py         # New: Celery task for triage scan
  api/routes/
    conventions.py         # New: CRUD endpoints for folder conventions
    triage.py              # New: triage results + history endpoints
    jobs.py                # Modified: add triage_scan dispatch
  config.py               # Modified: add triage_scan_cron setting
  celery_app.py            # Modified: add triage beat schedule + task include
  main.py                  # Modified: register new routers
  db/migrations/versions/
    xxx_add_triage_tables.py  # New: migration for conventions + issues tables
```

**Structure Decision**: Follows the existing project layout established in
001 and 002. Each concern gets its own model, schema, service, task, and
route module. No new directories needed.

## Complexity Tracking

No constitution violations to justify.
