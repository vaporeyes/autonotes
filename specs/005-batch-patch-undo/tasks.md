# Tasks: Batch Patch Operations & Undo/Rollback

**Input**: Design documents from `/specs/005-batch-patch-undo/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Database schema changes, new enum values, and shared model infrastructure

- [x] T001 Add `reverted` to PatchStatus enum in app/models/patch_operation.py
- [x] T002 Add `batch_patch` to JobType enum in app/models/job.py
- [x] T003 Create Alembic migration for `reverted` patch status and `batch_patch` job type enum additions in app/db/migrations/versions/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schemas, reverse-apply logic, and services that all user stories depend on

- [x] T004 [P] Create batch patch Pydantic schemas (BatchPatchRequest, BatchPatchResult, NoteResult) in app/schemas/batch_patch.py
- [x] T005 [P] Create undo Pydantic schemas (UndoResponse, BatchUndoResponse, UndoDetail) in app/schemas/undo.py
- [x] T006 Add reverse_apply_patch() function to app/services/patch_engine.py that constructs and applies the inverse operation for each operation type
- [x] T007 Extend existing apply_patch flow in app/api/routes/patches.py to store `previous_value` in payload for `update_frontmatter_key` operations at apply time

**Checkpoint**: Foundation ready -- schemas, reverse-apply logic, and previous_value capture available for all stories

---

## Phase 3: User Story 1 - Batch Patch by Folder (Priority: P1)

**Goal**: Apply the same operation(s) to all notes in a folder with a single request, following existing risk-tiered approval.

**Independent Test**: POST /batch-patches with a folder path and add_tag operation, verify all notes in the folder receive the tag and per-note results are returned.

### Implementation for User Story 1

- [x] T008 [US1] Implement batch_patch_service with folder-based note selection (using ObsidianClient.list_folder), per-note patch application via patch_engine, and result aggregation in app/services/batch_patch_service.py
- [x] T009 [US1] Implement batch_patch Celery task with progress tracking for async execution of large batches in app/tasks/batch_patch_job.py
- [x] T010 [US1] Add batch_patch_job to task include list in app/celery_app.py
- [x] T011 [US1] Add `batch_patch` to _TASK_DISPATCH mapping in app/api/routes/jobs.py
- [x] T012 [US1] Create POST /batch-patches endpoint with sync/async threshold (<=10 sync, >10 async) in app/api/routes/batch_patches.py
- [x] T013 [US1] Register batch_patches router in app/main.py and add "Batch Patches" OpenAPI tag

**Checkpoint**: Batch folder patching fully operational. Can apply operations to all notes in a folder via single request.

---

## Phase 4: User Story 2 - Batch Patch by Similarity Query (Priority: P2)

**Goal**: Apply operations to notes matching a similarity search query using the existing embedding engine.

**Independent Test**: POST /batch-patches with a query and threshold, verify matching notes receive the operation.

### Implementation for User Story 2

- [x] T014 [US2] Add query-based note selection to batch_patch_service using similarity_service.search_similar in app/services/batch_patch_service.py
- [x] T015 [US2] Update POST /batch-patches endpoint to accept query/threshold/limit parameters alongside folder_path in app/api/routes/batch_patches.py

**Checkpoint**: Batch patching works with both folder path and similarity query selection.

---

## Phase 5: User Story 3 - Undo a Single Patch (Priority: P3)

**Goal**: Revert a single applied patch by reverse-applying the operation, with content hash verification.

**Independent Test**: Apply a patch, then POST /patches/{id}/undo, verify the note is restored and the patch status is `reverted`.

### Implementation for User Story 3

- [x] T016 [US3] Implement undo_service with single-patch undo logic (hash verification, reverse-apply, status update, audit log) in app/services/undo_service.py
- [x] T017 [US3] Add POST /patches/{patch_id}/undo endpoint in app/api/routes/patches.py

**Checkpoint**: Single-patch undo fully operational. Can revert any applied patch with hash verification.

---

## Phase 6: User Story 4 - Undo a Batch Operation (Priority: P4)

**Goal**: Revert all applied patches from a batch job, skipping diverged notes.

**Independent Test**: Apply a batch patch, then POST /jobs/{id}/undo, verify all notes are reverted and per-note results are reported.

### Implementation for User Story 4

- [x] T018 [US4] Add batch undo logic to undo_service (iterate job patches, skip diverged, aggregate results) in app/services/undo_service.py
- [x] T019 [US4] Add POST /jobs/{job_id}/undo endpoint in app/api/routes/jobs.py

**Checkpoint**: Batch undo fully operational. Can revert entire batch jobs with per-note conflict reporting.

---

## Phase 7: User Story 5 - Preview Batch Operations (Priority: P5)

**Goal**: Dry-run mode that previews which notes would be affected without applying changes.

**Independent Test**: POST /batch-patches with dry_run: true, verify response lists affected notes and no modifications occur.

### Implementation for User Story 5

- [x] T020 [US5] Add dry_run support to batch_patch_service (simulate patches without writing, return would_apply/would_skip status) in app/services/batch_patch_service.py
- [x] T021 [US5] Update POST /batch-patches endpoint to handle dry_run flag and return preview response in app/api/routes/batch_patches.py

**Checkpoint**: Dry-run preview works for both folder and query-based batch operations.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and validation

- [x] T022 Run ruff check and fix any lint issues across all new and modified files
- [x] T023 Update README.md with Batch Patch and Undo feature descriptions, new API endpoints, and updated architecture
- [x] T024 Update CLAUDE.md project structure with new files (batch_patches route, undo_service, batch_patch_service, batch_patch_job)
- [ ] T025 Run quickstart.md validation against running stack

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (enum values must exist for schemas and services)
- **US1 Batch Folder (Phase 3)**: Depends on Phase 2 (needs schemas, reverse-apply, and batch service)
- **US2 Batch Query (Phase 4)**: Depends on US1 (extends batch_patch_service and endpoint)
- **US3 Single Undo (Phase 5)**: Depends on Phase 2 (needs reverse-apply); can parallel with US1/US2
- **US4 Batch Undo (Phase 6)**: Depends on US3 (extends undo_service)
- **US5 Dry Run (Phase 7)**: Depends on US1 (extends batch_patch_service); can parallel with US3/US4
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Batch Folder)**: After Phase 2 -- no story dependencies
- **US2 (Batch Query)**: After US1 -- extends the same service and endpoint
- **US3 (Single Undo)**: After Phase 2 -- can parallel with US1/US2
- **US4 (Batch Undo)**: After US3 -- extends undo_service
- **US5 (Dry Run)**: After US1 -- extends batch_patch_service

### Within Each User Story

- Services before routes
- Routes before router registration
- Core implementation before integration

### Parallel Opportunities

Within Phase 2:
- T004, T005 can run in parallel (separate schema files)

Across stories:
- US1 (T008-T013) and US3 (T016-T017) can run in parallel once Phase 2 is complete
- US5 (T020-T021) can run in parallel with US3/US4 once US1 is complete

---

## Implementation Strategy

### MVP First (Batch Folder + Single Undo)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: US1 Batch Folder (T008-T013)
4. Complete Phase 5: US3 Single Undo (T016-T017)
5. **STOP and VALIDATE**: Test batch folder patching + undo via curl
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational -> Enums, schemas, reverse-apply ready
2. Add US1 -> Batch folder patching operational (MVP part 1)
3. Add US3 -> Single undo operational (MVP part 2)
4. Add US2 -> Query-based batch patching available
5. Add US4 -> Batch undo available
6. Add US5 -> Dry-run preview available
7. Polish -> Docs, lint, quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US3 (undo) can be built in parallel with US1 (batch folder) since they share only Phase 2 foundations
- US2 extends US1's service/endpoint, so it must come after US1
- US4 extends US3's service, so it must come after US3
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
