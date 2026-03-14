# Tasks: Note Similarity Engine

**Input**: Design documents from `/specs/004-note-similarity-engine/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Database schema, new dependencies, Docker changes, and shared model infrastructure

- [x] T001 Add pgvector, numpy, scikit-learn dependencies to pyproject.toml via `uv add pgvector numpy scikit-learn`
- [x] T002 Change PostgreSQL Docker image from `postgres:16-alpine` to `pgvector/pgvector:pg16-alpine` in docker-compose.yml
- [x] T003 Add `embed_notes` and `cluster_notes` to JobType enum in app/models/job.py
- [x] T004 Add `create_moc` to OpType enum in app/models/patch_operation.py
- [x] T005 [P] Create NoteEmbedding ORM model with VECTOR(1536) column in app/models/note_embedding.py
- [x] T006 [P] Create NoteCluster and ClusterMember ORM models in app/models/note_cluster.py
- [x] T007 [P] Create DuplicatePair ORM model in app/models/duplicate_pair.py
- [x] T008 Create Alembic migration for note_embeddings, note_clusters, cluster_members, duplicate_pairs tables with pgvector extension and enum additions in app/db/migrations/versions/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Embedding service, config settings, and schemas that all user stories depend on

- [x] T009 [P] Add embedding configuration settings (EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, EMBEDDING_EXCLUDE_PATTERNS, EMBEDDING_BATCH_SIZE, SIMILARITY_DEFAULT_THRESHOLD, DUPLICATE_DEFAULT_THRESHOLD, CLUSTER_MIN_SIZE, MOC_TARGET_FOLDER, EMBEDDING_SCAN_CRON, CLUSTER_SCAN_CRON) in app/config.py
- [x] T010 [P] Create similarity Pydantic schemas (SimilaritySearchRequest, SimilaritySearchResponse, SimilarityResult, DuplicatePairResponse, DuplicatesResponse, EmbeddingStatusResponse) in app/schemas/similarity.py
- [x] T011 [P] Create cluster Pydantic schemas (ClusterResponse, ClusterListResponse, ClusterMemberResponse, MOCGenerateRequest, MOCDraftResponse) in app/schemas/cluster.py
- [x] T012 Implement embedding_service with OpenAI embedding generation, batch processing, content hash staleness detection, and incremental embedding in app/services/embedding_service.py

**Checkpoint**: Foundation ready -- embedding generation, schemas, and config available for all stories

---

## Phase 3: User Story 5 - Embed Vault Notes (Priority: P5, built first)

**Goal**: Run a background job that embeds all vault notes with incremental re-embedding support.

**Independent Test**: Trigger an embedding job via POST /jobs with job_type embed_notes, verify embeddings are stored, modify a note, re-run, verify only the changed note is re-embedded.

### Implementation for User Story 5

- [x] T013 [US5] Implement embedding Celery task with progress tracking and scope filtering in app/tasks/embedding_job.py
- [x] T014 [US5] Add embedding_job to task include list in app/celery_app.py
- [x] T015 [US5] Add embed_notes to _TASK_DISPATCH mapping and import in app/api/routes/jobs.py
- [x] T016 [US5] Implement GET /embeddings/status endpoint in app/api/routes/similarity.py
- [x] T017 [US5] Register similarity router in app/main.py and add OpenAPI tags (Similarity, Embeddings)

**Checkpoint**: Vault notes can be embedded via background job. Embedding status visible via API.

---

## Phase 4: User Story 1 - Find Similar Notes (Priority: P1)

**Goal**: Search for notes similar to a given note or free-text query, returning ranked results with scores.

**Independent Test**: Embed notes, then POST /similarity/search with a note_path. Verify ranked results with similarity scores. Repeat with a free-text query.

### Implementation for User Story 1

- [x] T018 [US1] Implement similarity_service with pgvector cosine search for note-path queries and free-text query embedding in app/services/similarity_service.py
- [x] T019 [US1] Implement POST /similarity/search endpoint with note_path and query support in app/api/routes/similarity.py
- [x] T020 [US1] Add on-the-fly embedding for unembedded source notes in app/services/similarity_service.py (calls embedding_service, persists result)

**Checkpoint**: Similarity search fully operational via API for both note paths and free-text queries.

---

## Phase 5: User Story 2 - Detect Near-Duplicate Notes (Priority: P2)

**Goal**: Identify note pairs exceeding a high-similarity threshold across the vault.

**Independent Test**: Run a cluster_notes job (which includes duplicate detection), then GET /similarity/duplicates/{job_id} and verify duplicate pairs with scores and excerpts.

### Implementation for User Story 2

- [x] T021 [US2] Implement duplicate detection logic in similarity_service: batch all-pairs cosine similarity via numpy, filter by threshold, store DuplicatePair records in app/services/similarity_service.py
- [x] T022 [US2] Implement GET /similarity/duplicates/{job_id} endpoint in app/api/routes/similarity.py

**Checkpoint**: Duplicate detection finds near-duplicate pairs. Results viewable via API.

---

## Phase 6: User Story 3 - Cluster Related Notes (Priority: P3)

**Goal**: Group embedded notes into topic clusters using HDBSCAN, with labels and an unclustered group.

**Independent Test**: Run a cluster_notes job, then GET /clusters/latest and verify topically related notes are grouped together with meaningful labels.

### Implementation for User Story 3

- [x] T023 [US3] Implement cluster_service with HDBSCAN clustering, label generation from note metadata (tags, titles, folder paths), and unclustered note handling in app/services/cluster_service.py
- [x] T024 [US3] Implement clustering Celery task (runs clustering + duplicate detection) with progress tracking in app/tasks/cluster_job.py
- [x] T025 [US3] Add cluster_job to task include list in app/celery_app.py
- [x] T026 [US3] Add cluster_notes to _TASK_DISPATCH mapping and import in app/api/routes/jobs.py
- [x] T027 [US3] Implement GET /clusters/latest and GET /clusters/{cluster_id} endpoints in app/api/routes/clusters.py
- [x] T028 [US3] Register clusters router in app/main.py and add Clusters OpenAPI tag

**Checkpoint**: Clustering produces labeled topic groups. Clusters and members viewable via API.

---

## Phase 7: User Story 4 - Generate MOC from Cluster (Priority: P4)

**Goal**: Generate a Map of Content Markdown draft from a cluster, write it to the vault through the patch approval system.

**Independent Test**: POST /clusters/{cluster_id}/moc, verify the draft contains wiki-links to all cluster members, approve it via POST /patches/{patch_id}/approve, verify the note is written to the vault.

### Implementation for User Story 4

- [x] T029 [US4] Implement moc_service with Markdown generation (title, summary, wiki-links grouped by sub-topic), existing MOC collision detection, and PatchOperation creation (op_type=create_moc, status=pending_approval) in app/services/moc_service.py
- [x] T030 [US4] Implement POST /clusters/{cluster_id}/moc endpoint in app/api/routes/clusters.py

**Checkpoint**: Full pipeline operational: embed, cluster, generate MOC, approve, write to vault.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Scheduled automation, documentation, and validation

- [x] T031 Add Celery beat schedule for periodic embedding job using EMBEDDING_SCAN_CRON config in app/celery_app.py
- [x] T032 Add Celery beat schedule for periodic clustering job using CLUSTER_SCAN_CRON config in app/celery_app.py
- [x] T033 Run ruff check and fix any lint issues across all new files
- [x] T034 Update README.md with Note Similarity Engine feature description, new API endpoints, and updated architecture
- [x] T035 Run quickstart.md validation against running stack

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (models and dependencies must exist)
- **US5 Embed (Phase 3)**: Depends on Phase 2 (needs embedding_service and schemas)
- **US1 Search (Phase 4)**: Depends on US5 (needs embeddings to exist)
- **US2 Duplicates (Phase 5)**: Depends on US5 (needs embeddings); can parallel with US1
- **US3 Clusters (Phase 6)**: Depends on US5 (needs embeddings); can parallel with US1/US2
- **US4 MOC (Phase 7)**: Depends on US3 (needs clusters to exist)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US5 (Embed)**: After Phase 2 -- no story dependencies (infrastructure story, built first)
- **US1 (Search)**: After US5 -- needs embeddings to search against
- **US2 (Duplicates)**: After US5 -- needs embeddings; can parallel with US1
- **US3 (Clusters)**: After US5 -- needs embeddings; can parallel with US1/US2
- **US4 (MOC)**: After US3 -- needs clusters to generate MOCs from

### Within Each User Story

- Models before services
- Services before routes
- Routes before router registration

### Parallel Opportunities

Within Phase 1:
- T005, T006, T007 can run in parallel (separate model files)

Within Phase 2:
- T009, T010, T011 can run in parallel (separate files)

Across stories:
- US1 (T018-T020), US2 (T021-T022), and US3 (T023-T028) can all run in parallel once US5 is complete

---

## Implementation Strategy

### MVP First (Embed + Search)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T012)
3. Complete Phase 3: US5 Embed (T013-T017)
4. Complete Phase 4: US1 Search (T018-T020)
5. **STOP and VALIDATE**: Test embedding + similarity search via curl
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational -> Models, schemas, config, embedding service ready
2. Add US5 -> Notes can be embedded via background job
3. Add US1 -> Similarity search operational (MVP)
4. Add US2 -> Duplicate detection available
5. Add US3 -> Topic clustering available
6. Add US4 -> MOC generation from clusters
7. Polish -> Scheduled automation, docs, lint, quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US5 (embedding) is built first despite being P5 in spec because it is infrastructure all other stories depend on
- US1-US3 can run in parallel once US5 is complete
- US4 depends on US3 (needs clusters)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
