# Tasks: AI Orchestrator

**Input**: Design documents from `/specs/001-ai-orchestrator/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.md

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `app/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Initialize Python 3.12 project with uv in pyproject.toml (FastAPI, Celery, httpx, SQLAlchemy, python-frontmatter, ruamel.yaml, markdown-it-py, pydantic-settings, alembic, psycopg2-binary, redis)
- [x] T002 Create app package structure with __init__.py files per plan.md layout (app/, app/api/, app/api/routes/, app/models/, app/schemas/, app/services/, app/tasks/, app/db/)
- [x] T003 [P] Create Dockerfile with Python 3.12 base, uv install, and app copy
- [x] T004 [P] Create docker-compose.yml with api, worker, redis, postgres services and extra_hosts for host.docker.internal
- [x] T005 [P] Create .env.example with OBSIDIAN_API_KEY, OBSIDIAN_API_URL, LLM_PROVIDER, LLM_API_KEY, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, LOG_RETENTION_DAYS

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T006 Implement settings via pydantic-settings in app/config.py (Obsidian API URL/key, DB URL, Redis URL, LLM provider/key, log retention days)
- [x] T007 Create Celery app singleton in app/celery_app.py with Redis broker and result backend configuration
- [x] T008 Create SQLAlchemy async session factory in app/db/session.py with engine and sessionmaker
- [x] T009 Initialize Alembic in alembic.ini and app/db/migrations/ with async PostgreSQL driver
- [x] T010 [P] Create Job SQLAlchemy model in app/models/job.py per data-model.md (id, celery_task_id, job_type enum, target_path, parameters, idempotency_key, status enum, progress_current, progress_total, result, error_message, timestamps)
- [x] T011 [P] Create PatchOperation SQLAlchemy model in app/models/patch_operation.py per data-model.md (id, job_id FK, target_path, operation_type enum, payload, idempotency_key, risk_level enum, status enum, before/after_hash, timestamps)
- [x] T012 [P] Create OperationLog SQLAlchemy model in app/models/operation_log.py per data-model.md (id, job_id FK, patch_operation_id FK, operation_name, target_path, before/after_hash, status enum, error_message, llm_notes_sent, created_at)
- [x] T013 [P] Create LLMInteraction SQLAlchemy model in app/models/llm_interaction.py per data-model.md (id, job_id FK, provider, model, notes_sent, prompt_tokens, completion_tokens, created_at)
- [x] T014 Generate initial Alembic migration for all 4 models including indexes (Job.idempotency_key partial unique, OperationLog.created_at, PatchOperation.idempotency_key unique)
- [x] T015 Create FastAPI app factory with lifespan handler in app/main.py (include all routers, mount API under /api/v1 prefix)
- [x] T016 Implement Obsidian REST API client in app/services/obsidian_client.py (httpx async client with Bearer token auth, SSL verify disabled for self-signed cert, methods: get_note, list_folder, patch_note, execute_command, health_check)
- [x] T017 [P] Implement health check endpoint in app/api/routes/health.py (GET /health checking Obsidian API, Redis, Postgres connectivity)
- [x] T018 [P] Create shared error response schema and exception handlers in app/api/routes/__init__.py per contracts/api.md error format (NOT_FOUND, CONFLICT, OBSIDIAN_UNREACHABLE, OBSIDIAN_ERROR, VALIDATION_ERROR, LLM_ERROR)

**Checkpoint**: Foundation ready -- user story implementation can now begin

---

## Phase 3: User Story 1 - Read and Analyze Vault Notes (Priority: P1) -- MVP

**Goal**: Parse and return structured note content (frontmatter, headings, tags, backlinks, word count) for individual notes and folders.

**Independent Test**: Request analysis of a known note, verify parsed frontmatter keys, tags, and body sections match the original file.

### Implementation for User Story 1

- [x] T019 [P] [US1] Create Note and NoteSummary Pydantic response schemas in app/schemas/note.py per contracts/api.md (file_path, frontmatter, headings, tags, backlinks, word_count, last_modified, content_hash; folder response with note_count and notes list)
- [x] T020 [US1] Implement note parser service in app/services/note_parser.py (parse frontmatter via python-frontmatter+ruamel.yaml, extract headings/links/tags via markdown-it-py, extract wikilinks via regex, compute SHA-256 content hash, compute word count)
- [x] T021 [US1] Implement GET /notes/{path} route in app/api/routes/notes.py (fetch note via obsidian_client, parse via note_parser, return Note schema; 404 if not found)
- [x] T022 [US1] Implement GET /notes/folder/{path} route in app/api/routes/notes.py (list folder via obsidian_client, parse each note into NoteSummary, support recursive query param)

**Checkpoint**: User Story 1 fully functional -- can read and analyze any note or folder

---

## Phase 4: User Story 2 - Surgical Edit via Patch Operations (Priority: P2)

**Goal**: Apply idempotent, domain-specific patch operations (add-tag, add-backlink, update-frontmatter-key, append-body) with content hash snapshots and operation logging.

**Independent Test**: Apply a patch to a known note, re-read to confirm only targeted fields changed. Apply same patch again, confirm no-op.

### Implementation for User Story 2

- [x] T023 [P] [US2] Create Patch request/response Pydantic schemas in app/schemas/patch.py per contracts/api.md (PatchRequest with target_path and operations list, PatchResult with per-op status, approve/reject responses)
- [x] T024 [P] [US2] Create OperationLog Pydantic response schema in app/schemas/log.py per contracts/api.md
- [x] T025 [US2] Implement patch engine service in app/services/patch_engine.py (apply_patch with check-before-write idempotency guards: check tag exists before add_tag, check backlink exists before add_backlink; use python-frontmatter for frontmatter key-level merge; use markdown-it-py .map offsets for body splice under heading; classify risk level per data-model.md; compute before/after content hashes)
- [x] T026 [US2] Implement operation log service in app/services/log_service.py (create_log entry in OperationLog table, query logs with filtering by target_path/operation_name/status/date range, log retention purge for entries older than configured days)
- [x] T027 [US2] Implement POST /patches route in app/api/routes/patches.py (accept PatchRequest, create Job+PatchOperation records, auto-apply low-risk ops via patch_engine, mark high-risk ops as pending_approval, log all via log_service, return PatchResult; 409 on content hash conflict)
- [x] T028 [US2] Implement POST /patches/{patch_id}/approve and POST /patches/{patch_id}/reject routes in app/api/routes/patches.py (approve: re-verify content hash, apply via patch_engine, log; reject: mark as skipped; 404/409 error handling)
- [x] T029 [US2] Implement GET /logs route in app/api/routes/logs.py per contracts/api.md (query params: target_path, operation_name, status, since, until, limit; return paginated log entries)

**Checkpoint**: User Story 2 fully functional -- can patch notes surgically with idempotency and audit trail

---

## Phase 5: User Story 3 - Execute Obsidian Commands (Priority: P3)

**Goal**: List available Obsidian commands and execute them by ID through the orchestrator API.

**Independent Test**: Trigger a known Obsidian command, verify execution status returned.

### Implementation for User Story 3

- [x] T030 [US3] Implement command forwarding service in app/services/command_service.py (list_commands via obsidian_client GET /commands/, execute_command via obsidian_client POST /commands/{id}/, log execution via log_service)
- [x] T031 [US3] Implement GET /commands route in app/api/routes/commands.py per contracts/api.md (return list of available commands with id and name)
- [x] T032 [US3] Implement POST /commands/{command_id} route in app/api/routes/commands.py per contracts/api.md (execute command, return status; 404 for unknown command; 502 for Obsidian unreachable)

**Checkpoint**: User Story 3 fully functional -- can list and execute Obsidian commands

---

## Phase 6: User Story 4 - Vault Scan with Task Queue (Priority: P4)

**Goal**: Submit long-running vault scans as background tasks, track progress, and prevent duplicate scans.

**Independent Test**: Start a scan on a folder with known notes, poll for progress, verify result matches expected counts.

### Implementation for User Story 4

- [x] T033 [P] [US4] Create Job request/response Pydantic schemas in app/schemas/job.py per contracts/api.md (JobRequest with job_type/target_path/parameters, JobStatus with progress, JobList with filtering)
- [x] T034 [US4] Implement job service in app/services/job_service.py (create_job with idempotency_key dedup check against pending/running jobs, get_job status from DB + Celery AsyncResult for in-flight progress, list_jobs with filtering, cancel_job)
- [x] T035 [US4] Implement vault scan Celery task in app/tasks/vault_scan.py (bind=True for self.update_state PROGRESS, iterate folder notes via obsidian_client, parse each via note_parser, scan for missing backlinks/orphaned links/tag issues, update Job progress in DB, store results on completion)
- [x] T036 [US4] Implement POST /jobs route in app/api/routes/jobs.py per contracts/api.md (accept JobRequest, dedup via job_service, dispatch Celery task, return 201 new or 200 existing)
- [x] T037 [US4] Implement GET /jobs/{job_id}, GET /jobs, POST /jobs/{job_id}/cancel routes in app/api/routes/jobs.py per contracts/api.md (status with progress, list with filtering, cancel with state transition)

**Checkpoint**: User Story 4 fully functional -- can run and track background vault scans

---

## Phase 7: User Story 5 - Monitoring UI and Manual Cleanup Jobs (Priority: P5)

**Goal**: Vault Cleanup detects orphaned backlinks, inconsistent tags, and missing frontmatter. Monitoring via Swagger UI with log filtering.

**Independent Test**: Open Swagger UI, verify logs visible, trigger cleanup job and track progress.

### Implementation for User Story 5

- [x] T038 [US5] Implement vault cleanup Celery task in app/tasks/vault_cleanup.py (scan vault for orphaned backlinks, duplicate/inconsistent tags, missing standard frontmatter keys; classify each fix as low-risk or high-risk per data-model.md; auto-apply low-risk fixes via patch_engine; create pending_approval PatchOperations for high-risk fixes; update Job progress; log all via log_service)
- [x] T039 [US5] Implement log purge Celery beat task in app/tasks/log_purge.py (periodic task that deletes OperationLog entries older than LOG_RETENTION_DAYS, register with Celery beat schedule in celery_app.py)
- [x] T040 [US5] Add vault_cleanup job type support to POST /jobs route in app/api/routes/jobs.py (dispatch vault_cleanup Celery task when job_type is vault_cleanup)
- [x] T041 [US5] Configure FastAPI Swagger UI metadata in app/main.py (title, description, version, tags for grouping endpoints by resource: Notes, Patches, Commands, Jobs, AI, Logs, Health)

**Checkpoint**: User Story 5 fully functional -- cleanup jobs run, logs purge on schedule, Swagger UI organized

---

## Phase 8: AI Capabilities (FR-015 through FR-018)

**Purpose**: LLM-powered analysis, suggestions, and conversational interface. Cross-cutting capability supporting FR-015/016/017/018.

- [x] T042 [P] Create AI request/response Pydantic schemas in app/schemas/ai.py per contracts/api.md (AnalyzeRequest with target_path and analysis_type enum, ChatRequest with question and scope, ChatResponse with answer/sources/notes_sent)
- [x] T043 Implement LLM provider abstraction in app/services/llm_provider.py (abstract base with complete/embed methods, Claude implementation via Anthropic SDK, OpenAI implementation via OpenAI SDK, factory function from config LLM_PROVIDER setting)
- [x] T044 Implement AI service in app/services/ai_service.py (analyze: read notes via obsidian_client, send to LLM for backlink/tag/summary/cleanup suggestions, classify suggestions as low/high risk PatchOperations; chat: search vault via obsidian_client, send relevant notes to LLM, return grounded answer with sources; log all LLM calls to LLMInteraction table via log_service)
- [x] T045 Implement AI analysis Celery task in app/tasks/ai_analysis.py (background task wrapping ai_service.analyze, with progress tracking for multi-note analysis)
- [x] T046 Implement POST /ai/analyze route in app/api/routes/ai.py per contracts/api.md (create job, dispatch ai_analysis Celery task, return job ID)
- [x] T047 Implement POST /ai/chat route in app/api/routes/ai.py per contracts/api.md (synchronous LLM call via ai_service.chat, return ChatResponse with answer, sources, notes_sent, provider info)

**Checkpoint**: AI capabilities functional -- can analyze notes, get suggestions, and chat about vault content

---

## Phase 9: Polish and Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T048 [P] Create .env.example documentation with all required and optional environment variables
- [x] T049 [P] Add ABOUTME comments to all Python files per CLAUDE.md guidelines
- [x] T050 Validate idempotency across all patch operation types (run each operation twice, confirm identical vault state per SC-004 and constitution Principle V)
- [ ] T051 Validate quickstart.md workflow end-to-end (follow all steps, verify all checklist items pass)
- [x] T052 Review all write operations use narrowest available mutation API per constitution Principle II (no full-file rewrites, all patches use key-level merge or line-range splice)

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion -- BLOCKS all user stories
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - US1 (Phase 3): No dependencies on other stories
  - US2 (Phase 4): Depends on US1 (uses note_parser from US1 for pre-patch reads)
  - US3 (Phase 5): No dependencies on other stories (only needs obsidian_client from Phase 2)
  - US4 (Phase 6): Depends on US1 (uses note_parser for scan analysis)
  - US5 (Phase 7): Depends on US2 (uses patch_engine for cleanup fixes) and US4 (uses job infrastructure)
- **AI Capabilities (Phase 8)**: Depends on US1 (note reading), US2 (patch operations), and US4 (job queue)
- **Polish (Phase 9)**: Depends on all previous phases being complete

### Parallel Opportunities

- Phase 1: T003, T004, T005 can run in parallel
- Phase 2: T010, T011, T012, T013 (all models) can run in parallel; T017, T018 can run in parallel
- Phase 3: T019 can run in parallel with Phase 2 models
- Phase 4: T023, T024 can run in parallel
- Phase 5: US3 (Phase 5) can run in parallel with US2 (Phase 4) since they share no code
- Phase 8: T042 can run in parallel with other schema tasks

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all models in parallel (different files, no dependencies):
Task: T010 "Create Job model in app/models/job.py"
Task: T011 "Create PatchOperation model in app/models/patch_operation.py"
Task: T012 "Create OperationLog model in app/models/operation_log.py"
Task: T013 "Create LLMInteraction model in app/models/llm_interaction.py"

# Launch health + error handling in parallel:
Task: T017 "Implement health endpoint in app/api/routes/health.py"
Task: T018 "Create error handlers in app/api/routes/__init__.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL -- blocks all stories)
3. Complete Phase 3: User Story 1 (Read and Analyze)
4. **STOP and VALIDATE**: Verify GET /notes/{path} returns parsed content
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational -> Foundation ready
2. Add User Story 1 -> Test independently -> Deploy/Demo (MVP!)
3. Add User Story 2 -> Test independently -> Surgical edits working
4. Add User Story 3 -> Test independently -> Command execution working
5. Add User Story 4 -> Test independently -> Background scans working
6. Add User Story 5 -> Test independently -> Cleanup + monitoring working
7. Add AI Capabilities -> Test independently -> Full AI assistant
8. Polish -> Final validation

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All write operations must go through patch_engine for idempotency (constitution Principle V)
- All mutations must be logged via log_service (FR-008)
- No note content sent to LLM without explicit user trigger (constitution Principle III)
