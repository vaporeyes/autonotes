# Implementation Plan: Note Similarity Engine

**Branch**: `004-note-similarity-engine` | **Date**: 2026-03-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-note-similarity-engine/spec.md`

## Summary

Build an embeddings-based note similarity engine that generates OpenAI vector embeddings for vault notes, stores them in PostgreSQL, and exposes similarity search (by note path or free-text query), near-duplicate detection, topic clustering, and MOC (Map of Content) generation endpoints. Integrates with the existing job system for background processing and the patch system for MOC approval workflow.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Celery, SQLAlchemy, OpenAI SDK (embeddings), numpy (vector math), scikit-learn (clustering)
**Storage**: PostgreSQL 16 (note_embeddings, note_clusters tables), Redis 7 (Celery broker)
**Testing**: pytest
**Target Platform**: Linux server (Docker Compose)
**Project Type**: Web service (extends existing FastAPI application)
**Performance Goals**: Similarity search < 3s for 1,000 notes; embedding throughput >= 100 notes/min
**Constraints**: Vault < 10,000 notes; embeddings stored in PostgreSQL (no separate vector store); OpenAI-only embedding provider
**Scale/Scope**: Single vault, single user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Data Integrity | PASS | MOC writes go through existing patch system with content hash verification. Embedding operations are read-only against vault content. No note content is modified during embedding or search. |
| II. Surgical Updates | PASS | MOC creation uses the patch system to write new files. No existing notes are modified by this feature. |
| III. Local-First Privacy | PASS with caveat | Note content is sent to OpenAI for embedding. This is an explicit user-triggered operation (same consent model as POST /ai/analyze). All embedding calls are logged with note paths and token counts via LLMInteraction records. |
| IV. Extensibility | PASS | Embedding service is a self-contained module. Similarity, clustering, and MOC generation are separate services with declared interfaces. |
| V. Idempotency | PASS | Embedding uses content hash to detect staleness -- re-embedding unchanged notes is a no-op. Duplicate detection is a pure read. MOC generation creates drafts that require approval before writing. |

**Operational Constraints**:
- Conflict resolution: Content hash checked before MOC write (standard patch system behavior)
- Vault boundaries: Scoped to single vault (consistent with existing design)
- Backup granularity: MOC writes are new files (no overwrite risk); embedding is metadata-only

## Project Structure

### Documentation (this feature)

```text
specs/004-note-similarity-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
app/
├── models/
│   ├── note_embedding.py    # NoteEmbedding ORM model
│   └── note_cluster.py      # NoteCluster + ClusterMember ORM models
├── schemas/
│   ├── similarity.py        # Similarity search request/response schemas
│   └── cluster.py           # Cluster and MOC schemas
├── services/
│   ├── embedding_service.py # OpenAI embedding generation + storage
│   ├── similarity_service.py # Vector similarity search + duplicate detection
│   ├── cluster_service.py   # Clustering algorithm + label generation
│   └── moc_service.py       # MOC Markdown generation from clusters
├── tasks/
│   ├── embedding_job.py     # Celery task: vault-wide embedding
│   └── cluster_job.py       # Celery task: clustering + duplicate detection
├── api/routes/
│   ├── similarity.py        # GET /similarity/search, GET /similarity/duplicates
│   └── clusters.py          # GET /clusters, GET /clusters/{id}, POST /clusters/{id}/moc
└── db/migrations/versions/
    └── xxxx_add_embeddings.py  # Alembic migration for new tables
```

**Structure Decision**: Follows existing project conventions. New files only -- no modifications to existing services except registering new routes in `main.py`, adding job types to `job.py`, task includes in `celery_app.py`, and config settings in `config.py`.
