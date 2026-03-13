# Tasks: Auto-Triage for Vault Notes

**Input**: Design documents from `/specs/003-auto-triage/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Database schema and shared model infrastructure

- [x] T001 Add `triage_scan` to JobType enum in app/models/job.py
- [x] T002 [P] Create FolderConvention ORM model in app/models/folder_convention.py
- [x] T003 [P] Create TriageIssue ORM model in app/models/triage_issue.py
- [x] T004 Create Alembic migration for folder_conventions and triage_issues tables, issue_type_enum, triage_resolution_enum, and job_type_enum addition in app/db/migrations/versions/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Convention service and schemas that all user stories depend on

- [x] T005 [P] Create convention Pydantic schemas (request/response) in app/schemas/convention.py
- [x] T006 [P] Create triage Pydantic schemas (issue, scan result, history) in app/schemas/triage.py
- [x] T007 Implement convention_service with CRUD operations and inheritance resolution (prefix-match query + merge) in app/services/convention_service.py
- [x] T008 Add triage_scan_cron and triage_scan_scope config settings in app/config.py

**Checkpoint**: Foundation ready -- convention storage and schemas available for all stories

---

## Phase 3: User Story 1 - Define Folder Conventions (Priority: P1)

**Goal**: Users can create, read, update, and delete folder conventions via API, with inheritance resolution for nested folders.

**Independent Test**: Create a convention for `projects/`, create a sub-convention for `projects/active/`, call the resolve endpoint for a note in `projects/active/` and verify merged rules.

### Implementation for User Story 1

- [x] T009 [US1] Implement convention CRUD routes (POST, GET list, GET by ID, PUT, DELETE) in app/api/routes/conventions.py
- [x] T010 [US1] Implement GET /conventions/resolve endpoint for merged convention lookup in app/api/routes/conventions.py
- [x] T011 [US1] Register conventions router in app/main.py and add OpenAPI tag

**Checkpoint**: Convention CRUD and inheritance resolution fully operational via API

---

## Phase 4: User Story 2 - Scan Recent Notes and Detect Issues (Priority: P2)

**Goal**: System scans recently modified notes, compares against folder conventions, and reports detected issues (missing frontmatter, missing tags, missing backlinks, tag normalization).

**Independent Test**: Define a convention requiring `status` field, create a note without it, trigger a triage scan via POST /jobs, and verify the issue appears in scan results.

### Implementation for User Story 2

- [x] T012 [US2] Implement triage_service core: scan loop that reads notes, resolves conventions, and detects issues in app/services/triage_service.py
- [x] T013 [US2] Implement triage_scan Celery task with progress tracking in app/tasks/triage_scan.py
- [x] T014 [US2] Add triage_scan to task include list in app/celery_app.py
- [x] T015 [US2] Add triage_scan to _TASK_DISPATCH mapping and import in app/api/routes/jobs.py
- [x] T016 [US2] Implement GET /triage/results/{job_id} endpoint in app/api/routes/triage.py
- [x] T017 [US2] Register triage router in app/main.py and add OpenAPI tag

**Checkpoint**: Triage scans detect and report issues. No fixes applied yet.

---

## Phase 5: User Story 3 - Auto-Apply Low-Risk Fixes (Priority: P3)

**Goal**: Low-risk issues (missing frontmatter with defaults, tag normalization, missing expected tags) are automatically fixed during the triage scan via the existing patch engine.

**Independent Test**: Define a convention with `status` defaulting to `draft`, create a note missing that field, run a triage scan, verify the field was added to the note and a PatchOperation record was created.

### Implementation for User Story 3

- [x] T018 [US3] Extend triage_service scan loop to auto-apply low-risk fixes using patch_engine.apply_patch() with content hash verification in app/services/triage_service.py
- [x] T019 [US3] Create PatchOperation records and operation log entries for each auto-applied fix in app/services/triage_service.py

**Checkpoint**: Low-risk fixes auto-apply during scans. High-risk issues detected but not acted on.

---

## Phase 6: User Story 4 - Queue High-Risk Suggestions for Approval (Priority: P4)

**Goal**: High-risk issues (missing backlinks) create pending PatchOperation records that users approve or reject through the existing patch endpoints. Rejected suggestions are not re-surfaced until the note is modified.

**Independent Test**: Define a convention with a backlink target, create a note missing the backlink, run a triage scan, verify a pending_approval PatchOperation exists, reject it, re-run the scan, verify no new suggestion is created. Modify the note, re-run, verify suggestion reappears.

### Implementation for User Story 4

- [x] T020 [US4] Extend triage_service to create pending PatchOperation records for high-risk issues in app/services/triage_service.py
- [x] T021 [US4] Implement rejection tracking: populate rejected_hash and rejected_at on TriageIssue when patch is rejected in app/services/triage_service.py
- [x] T022 [US4] Add rejection suppression check to triage scan loop (compare note modification time against rejection timestamp) in app/services/triage_service.py

**Checkpoint**: Full triage pipeline operational: detect, auto-fix low-risk, queue high-risk, suppress rejected suggestions.

---

## Phase 7: User Story 5 - View Triage Results and History (Priority: P5)

**Goal**: Users can view detailed results of any triage scan and browse scan history with summary counts.

**Independent Test**: Run a triage scan, call GET /triage/results/{job_id} and verify issues/fixes/suggestions listed. Run multiple scans, call GET /triage/history and verify reverse-chronological listing.

### Implementation for User Story 5

- [x] T023 [US5] Implement GET /triage/history endpoint with scope filter, since, and limit params in app/api/routes/triage.py

**Checkpoint**: All user stories complete and independently testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Scheduled automation and validation

- [x] T024 Add Celery beat schedule for periodic triage scans using triage_scan_cron config in app/celery_app.py
- [x] T025 Run ruff check and fix any lint issues across all new files
- [ ] T026 Run quickstart.md validation against running stack

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (models must exist for schemas and services)
- **User Stories (Phase 3+)**: All depend on Phase 2 completion
  - US1 (conventions CRUD) can start after Phase 2
  - US2 (scan + detect) depends on US1 (needs conventions to exist)
  - US3 (auto-apply) depends on US2 (extends the scan loop)
  - US4 (high-risk queue) depends on US3 (extends the scan loop)
  - US5 (results view) depends on US2 (needs scan results to exist)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 -- no story dependencies
- **US2 (P2)**: After US1 -- needs conventions to scan against
- **US3 (P3)**: After US2 -- extends the scan loop with auto-apply
- **US4 (P4)**: After US3 -- extends the scan loop with pending patches
- **US5 (P5)**: After US2 -- needs scan results data; can parallel with US3/US4

### Within Each User Story

- Models before services
- Services before routes
- Routes before router registration

### Parallel Opportunities

Within Phase 1:
- T002 and T003 can run in parallel (separate model files)

Within Phase 2:
- T005 and T006 can run in parallel (separate schema files)

Across stories:
- US5 (T023) can run in parallel with US3/US4 once US2 is complete

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T008)
3. Complete Phase 3: User Story 1 (T009-T011)
4. **STOP and VALIDATE**: Test convention CRUD and inheritance via curl
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational -> Models, schemas, config ready
2. Add US1 -> Convention management operational (MVP)
3. Add US2 -> Triage scans detect issues
4. Add US3 -> Low-risk fixes auto-apply
5. Add US4 -> High-risk suggestions queued with rejection tracking
6. Add US5 -> Full results visibility
7. Polish -> Scheduled automation, lint, quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2-US4 build incrementally on triage_service.py -- sequential, not parallel
- US5 can parallel with US3/US4 since it only reads scan results
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
