# Tasks: Web Dashboard

**Input**: Design documents from `/specs/006-web-dashboard/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Static file directory structure, SPA shell, shared CSS, routing, and API client

- [x] T001 Create static file directory structure (app/static/, app/static/css/, app/static/js/, app/static/js/views/, app/static/js/components/)
- [x] T002 Create SPA shell HTML with nav bar, route links, and app container in app/static/index.html
- [x] T003 Create dark theme CSS with layout, design tokens, and responsive styles in app/static/css/styles.css
- [x] T004 Create hash-based router and nav highlight logic in app/static/js/app.js
- [x] T005 Create API client module with fetch wrappers for GET/POST in app/static/js/api.js
- [x] T006 Mount StaticFiles directory and configure static file serving in app/main.py

**Checkpoint**: SPA shell loads at /dashboard/, nav works, routes switch views, API client ready.

---

## Phase 2: Foundational (Backend Additions)

**Purpose**: New API endpoints that multiple views depend on

- [x] T007 [P] Create Pydantic schemas for PatchListItem and PatchListResponse in app/schemas/patch.py
- [x] T008 [P] Create Pydantic schema for VaultStructureNode in app/schemas/note.py
- [x] T009 Add GET /patches endpoint with status/limit/offset filtering in app/api/routes/patches.py
- [x] T010 Add GET /vault-structure endpoint with recursive folder tree in app/api/routes/notes.py

**Checkpoint**: Foundation ready. `curl /api/v1/patches?status=pending_approval` and `curl /api/v1/vault-structure` return data.

---

## Phase 3: User Story 1 - System Dashboard (Priority: P1)

**Goal**: Landing page with service health indicators, vault metrics, sparklines, stale-data warning, and health scan trigger.

**Independent Test**: Open /dashboard/#/dashboard, verify health status indicators, vault metrics, sparklines render, and "Run Scan" button works.

### Implementation for User Story 1

- [x] T011 [US1] Create sparkline SVG component in app/static/js/components/sparkline.js
- [x] T012 [US1] Implement dashboard view with health status, vault metrics, sparklines, stale warning, and scan button in app/static/js/views/dashboard.js
- [x] T013 [US1] Register dashboard view in router in app/static/js/app.js

**Checkpoint**: Dashboard view fully operational. Shows health indicators, vault metrics, sparklines, and can trigger health scans.

---

## Phase 4: User Story 2 - Notes Browser (Priority: P2)

**Goal**: Folder tree navigation, note list per folder, note detail panel, AI analysis triggers.

**Independent Test**: Open #/notes, expand folder tree, select folder to see notes, select note to see detail, trigger AI suggest tags.

### Implementation for User Story 2

- [x] T014 [US2] Create folder tree component with expand/collapse in app/static/js/components/folder-tree.js
- [x] T015 [US2] Implement notes browser view with three-panel layout (tree, list, detail) in app/static/js/views/notes.js
- [x] T016 [US2] Register notes view in router in app/static/js/app.js

**Checkpoint**: Notes Browser fully operational. Folder tree loads, notes display, detail panel shows parsed content, AI analysis buttons work.

---

## Phase 5: User Story 3 - Patches and Approvals (Priority: P3)

**Goal**: Pending patches list with approve/reject, confirmation dialogs, collapsible history.

**Independent Test**: Open #/patches, see pending patches, approve one, reject one, verify both appear in history.

### Implementation for User Story 3

- [x] T017 [US3] Implement patches view with pending list, approve/reject with confirmation, and collapsible history in app/static/js/views/patches.js
- [x] T018 [US3] Register patches view in router in app/static/js/app.js

**Checkpoint**: Patches view fully operational. Can list, approve, reject patches with confirmation and history.

---

## Phase 6: User Story 4 - Jobs Monitor (Priority: P4)

**Goal**: Job list with status, progress bars, cancel button, filters, job detail.

**Independent Test**: Open #/jobs, see job list, filter by status, observe progress bar on running job, cancel a job.

### Implementation for User Story 4

- [x] T019 [US4] Create progress bar component in app/static/js/components/progress-bar.js
- [x] T020 [US4] Implement jobs view with list, filters, progress polling, cancel, and detail expansion in app/static/js/views/jobs.js
- [x] T021 [US4] Register jobs view in router in app/static/js/app.js

**Checkpoint**: Jobs view fully operational. Shows jobs with progress, supports filtering and cancellation.

---

## Phase 7: User Story 5 - AI Chat (Priority: P5)

**Goal**: Chat interface with scrollable conversation history, scope selector, source note links.

**Independent Test**: Open #/chat, type a question, receive answer with sources, verify conversation history persists in session.

### Implementation for User Story 5

- [x] T022 [US5] Implement chat view with message history, input, scope selector, and source note links in app/static/js/views/chat.js
- [x] T023 [US5] Register chat view in router in app/static/js/app.js

**Checkpoint**: AI Chat fully operational. Conversation history maintained, scope selector works, source notes clickable.

---

## Phase 8: User Story 6 - Audit Logs (Priority: P6)

**Goal**: Filterable, paginated audit log table.

**Independent Test**: Open #/logs, see log entries, filter by target path, paginate through results.

### Implementation for User Story 6

- [x] T024 [US6] Implement logs view with table, filters, and pagination in app/static/js/views/logs.js
- [x] T025 [US6] Register logs view in router in app/static/js/app.js

**Checkpoint**: Audit Logs fully operational. Filterable, paginated log table works.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Lint, documentation, validation

- [x] T026 Run ruff check and fix any lint issues across all new and modified Python files
- [x] T027 Update README.md with Web Dashboard feature description and access instructions
- [x] T028 Update CLAUDE.md project structure with new files (static/, new endpoints)
- [ ] T029 Run quickstart.md validation against running stack

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (static files must be mountable, schemas extend existing files)
- **US1 Dashboard (Phase 3)**: Depends on Phase 1 (needs router, API client, CSS)
- **US2 Notes Browser (Phase 4)**: Depends on Phase 2 (needs GET /vault-structure endpoint)
- **US3 Patches (Phase 5)**: Depends on Phase 2 (needs GET /patches endpoint)
- **US4 Jobs (Phase 6)**: Depends on Phase 1 (uses only existing GET /jobs endpoint)
- **US5 AI Chat (Phase 7)**: Depends on Phase 1 (uses only existing POST /ai/chat endpoint)
- **US6 Logs (Phase 8)**: Depends on Phase 1 (uses only existing GET /logs endpoint)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Dashboard)**: After Phase 1 -- no story dependencies, no new backend endpoints needed
- **US2 (Notes Browser)**: After Phase 2 -- needs GET /vault-structure
- **US3 (Patches)**: After Phase 2 -- needs GET /patches
- **US4 (Jobs)**: After Phase 1 -- can parallel with US1
- **US5 (AI Chat)**: After Phase 1 -- can parallel with US1
- **US6 (Logs)**: After Phase 1 -- can parallel with US1

### Within Each User Story

- Components before views
- Views before router registration
- Backend endpoints before frontend views that depend on them

### Parallel Opportunities

After Phase 1:
- US1 (T011-T013), US4 (T019-T021), US5 (T022-T023), US6 (T024-T025) can all run in parallel

After Phase 2:
- US2 (T014-T016) and US3 (T017-T018) can run in parallel

Within Phase 2:
- T007 and T008 can run in parallel (different schema files)

---

## Implementation Strategy

### MVP First (Dashboard Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 3: US1 Dashboard (T011-T013)
3. **STOP and VALIDATE**: Open /dashboard/ in browser, verify health status and metrics
4. Deploy/demo if ready

### Incremental Delivery

1. Setup -> SPA shell, router, API client, static serving
2. Add US1 -> Dashboard with health and metrics (MVP)
3. Add Phase 2 -> Backend endpoints for patches list and vault structure
4. Add US2 -> Notes Browser operational
5. Add US3 -> Patches & Approvals operational
6. Add US4 -> Jobs Monitor operational
7. Add US5 -> AI Chat operational
8. Add US6 -> Audit Logs operational
9. Polish -> Lint, docs, quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 (Dashboard) can be built immediately after setup since it only uses existing endpoints
- US4, US5, US6 also only need existing endpoints and can parallel with US1
- US2 and US3 depend on Phase 2 backend additions
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
