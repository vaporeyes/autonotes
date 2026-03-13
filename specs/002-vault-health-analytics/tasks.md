# Tasks: Vault Health Analytics

**Input**: Design documents from `/specs/002-vault-health-analytics/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.md

**Tests**: Not explicitly requested. Test tasks omitted.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Database migration and shared model infrastructure

- [x] T001 Create Alembic migration adding `vault_health_scan` to `job_type_enum` and creating `health_snapshots` table in app/db/migrations/versions/
- [x] T002 Create HealthSnapshot SQLAlchemy model in app/models/health_snapshot.py
- [x] T003 Add `vault_health_scan` to JobType enum in app/models/job.py

---

## Phase 2: Foundational

**Purpose**: Health analytics service with metric computation -- MUST complete before any endpoint or task work

- [x] T004 Create health response Pydantic schemas (HealthSnapshotResponse, HealthTrendResponse, DashboardResponse) in app/schemas/health.py
- [x] T005 Implement Union-Find data structure and graph analysis functions (cluster detection, orphan identification) in app/services/health_service.py
- [x] T006 Implement metric computation functions (tag distribution, backlink density, orphan ratio) in app/services/health_service.py
- [x] T007 Implement composite health score calculation with normalization (orphan 30%, density 30%, connectivity 25%, tags 15%) in app/services/health_service.py

**Checkpoint**: Foundation ready -- health_service can compute all metrics from parsed note data

---

## Phase 3: User Story 1 - View Current Vault Health Metrics (Priority: P1) MVP

**Goal**: User submits a health scan job, system computes all four metrics plus composite score, returns a snapshot

**Independent Test**: Submit a vault_health_scan job via POST /jobs, wait for completion, retrieve snapshot via GET /vault-health/snapshot/{job_id} and verify all metrics are populated

### Implementation for User Story 1

- [x] T008 [US1] Implement the run_health_scan orchestrator function in app/services/health_service.py that accepts a scope parameter (folder path or "/" for full vault), iterates notes via obsidian_client, parses each with note_parser, computes all metrics, and returns a HealthSnapshot dict
- [x] T009 [US1] Create Celery task vault_health_scan in app/tasks/vault_health_scan.py with progress tracking (notes processed / total), calling health_service.run_health_scan and persisting the HealthSnapshot to PostgreSQL. Job deduplication is inherited from existing job_service via idempotency_key
- [x] T010 [US1] Add `app.tasks.vault_health_scan` to the Celery include list in app/celery_app.py
- [x] T011 [US1] Create vault health routes module in app/api/routes/vault_health.py with GET /vault-health/snapshot/{job_id} and GET /vault-health/latest endpoints
- [x] T012 [US1] Register vault_health router in app/main.py
- [x] T013 [US1] Wire vault_health_scan job type into existing POST /jobs dispatch logic in app/api/routes/jobs.py

**Checkpoint**: User can submit a health scan, monitor progress, and retrieve the full snapshot with all metrics

---

## Phase 4: User Story 2 - Track Health Metrics Over Time (Priority: P2)

**Goal**: Historical snapshots queryable as time-series, with deltas and rolling averages

**Independent Test**: Run 2+ health scans, then GET /vault-health/trends?metric=orphan_count and verify time-series data points with deltas

### Implementation for User Story 2

- [x] T014 [US2] Implement trend query functions in app/services/health_service.py: query snapshots by scope and date range, compute delta, 7-day and 30-day rolling averages
- [x] T015 [US2] Add GET /vault-health/trends endpoint in app/api/routes/vault_health.py returning HealthTrendResponse

**Checkpoint**: User can query historical trends for any metric across stored snapshots

---

## Phase 5: User Story 3 - Dashboard Endpoint (Priority: P3)

**Goal**: Single endpoint combining latest snapshot with trend summaries and staleness indicator

**Independent Test**: GET /vault-health/dashboard returns latest snapshot, trend deltas for all 5 metrics, and correct stale_data flag

### Implementation for User Story 3

- [x] T016 [US3] Implement dashboard aggregation function in app/services/health_service.py that combines latest snapshot with trend summaries for all 5 metrics and computes staleness
- [x] T017 [US3] Add GET /vault-health/dashboard endpoint in app/api/routes/vault_health.py returning DashboardResponse

**Checkpoint**: User gets a complete health overview in a single API call

---

## Phase 6: User Story 4 - Scheduled Health Scans (Priority: P4)

**Goal**: Automatic health scans via Celery beat at configurable intervals

**Independent Test**: Configure a scheduled scan, verify a new snapshot is created at the next beat interval

### Implementation for User Story 4

- [x] T018 [US4] Add HEALTH_SCAN_CRON, HEALTH_SCAN_SCOPE, and HEALTH_STALE_THRESHOLD_HOURS config settings to app/config.py
- [x] T019 [US4] Add Celery beat schedule entry for vault_health_scan in app/celery_app.py using the configured cron expression
- [x] T020 [US4] Add snapshot retention purge logic (delete snapshots older than 365 days) as a Celery beat task in app/tasks/vault_health_scan.py

**Checkpoint**: Health scans run automatically on schedule, old snapshots are purged

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, validation, and end-to-end verification

- [x] T021 Handle empty vault edge case (zero notes) in app/services/health_service.py -- return valid zero-value metrics
- [x] T022 Handle deleted-note-mid-scan edge case in app/services/health_service.py -- skip gracefully and record in skipped_notes
- [x] T023 Handle no-history edge case in trend and dashboard endpoints -- return descriptive empty responses per contract
- [ ] T024 Run quickstart.md verification workflow end-to-end against running stack

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- start immediately
- **Foundational (Phase 2)**: Depends on T002 (model) and T003 (enum)
- **US1 (Phase 3)**: Depends on all foundational tasks (T004-T007)
- **US2 (Phase 4)**: Depends on US1 (snapshots must exist to query trends)
- **US3 (Phase 5)**: Depends on US1 + US2 (dashboard combines both)
- **US4 (Phase 6)**: Depends on US1 (scheduled scan reuses scan logic)
- **Polish (Phase 7)**: Depends on all user stories

### User Story Dependencies

- **US1 (P1)**: Independent after foundational phase
- **US2 (P2)**: Requires US1 (needs snapshots to compute trends)
- **US3 (P3)**: Requires US1 + US2 (combines snapshot + trends)
- **US4 (P4)**: Requires US1 only (scheduled scan = automated US1)

### Within Each Phase

- Models before services
- Services before endpoints
- Celery tasks before route wiring

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- T005, T006, T007 build on each other sequentially in the same file
- T018, T019, T020 are in different files and could run in parallel

---

## Parallel Example: Phase 1 Setup

```bash
# These touch different files and can run together:
Task T002: "Create HealthSnapshot model in app/models/health_snapshot.py"
Task T003: "Add vault_health_scan to JobType enum in app/models/job.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: User Story 1 (T008-T013)
4. **STOP and VALIDATE**: Submit a health scan, verify all 4 metrics + composite score
5. Deploy if ready

### Incremental Delivery

1. Setup + Foundational -> core metric engine ready
2. Add US1 -> manual health scans work (MVP)
3. Add US2 -> historical trends queryable
4. Add US3 -> dashboard consolidates everything
5. Add US4 -> scans run automatically
6. Polish -> edge cases handled, end-to-end verified

---

## Notes

- All new Python files must start with two `# ABOUTME:` comment lines
- Use raw SQL in Alembic migration (matching pattern from initial schema)
- Health service is read-only (no vault writes) -- no patch_engine or log_service needed
- Reuse obsidian_client.list_folder(recursive=True) and note_parser.parse_note() for data collection
- Use task_session() (not async_session) in Celery tasks for event loop isolation
