# Implementation Plan: AI Orchestrator

**Branch**: `001-ai-orchestrator` | **Date**: 2026-03-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-orchestrator/spec.md`

## Summary

Build a FastAPI-based orchestrator that connects to an Obsidian vault
via the Local REST API plugin. The system reads and parses notes,
applies surgical patch operations (domain-specific ops translated to
Obsidian's native PATCH), executes Obsidian commands, runs background
vault scans via Celery+Redis, provides full AI assistant capabilities
(summaries, suggestions, chat) through configurable LLM providers,
and exposes a Swagger/Redoc monitoring interface. All operations are
idempotent, logged, and respect local-first privacy.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Celery, httpx, python-frontmatter, ruamel.yaml, markdown-it-py, SQLAlchemy
**Storage**: PostgreSQL 16 (persistent jobs/logs), Redis 7 (broker + transient results)
**Testing**: pytest + pytest-asyncio + httpx test client
**Target Platform**: Docker Compose (Linux containers), connecting to host-native Obsidian
**Project Type**: web-service (API-first with auto-generated Swagger UI)
**Performance Goals**: <2s note read, <1s single patch, 500 notes/30s folder scan
**Constraints**: All note content local-only except explicit AI ops; single vault; single user
**Scale/Scope**: Single user, vaults up to ~5000 notes, 1 API + 1 worker container

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How Addressed |
|-----------|--------|---------------|
| I. Data Integrity | PASS | FR-007: content hash snapshot before every write. PatchOperation records before/after hashes. Atomic failure recovery via hash comparison. |
| II. Surgical Updates | PASS | FR-004/005: domain-specific patch ops (add-tag, add-backlink, etc.) translate to Obsidian native PATCH headers. python-frontmatter for key-level frontmatter merge. markdown-it-py .map offsets for body splice. No full-file rewrites. |
| III. Local-First Privacy | PASS | FR-014: note content stays local by default. LLM calls only on explicit AI operations (FR-015/016/017). LLMInteraction entity logs every external transmission. |
| IV. Extensibility | PASS | Modular service layer: each operation type is a self-contained module. New patch types register via enum extension. LLM provider abstracted behind interface. Tool config via environment variables. |
| V. Idempotency | PASS | FR-006: all write ops check-before-write. PatchOperation.idempotency_key (hash of path+type+payload) prevents duplicates. Job dedup via idempotency_key + status index. Three-layer defense: DB key, deterministic Celery task ID, Redis lock. |

**Post-Phase 1 re-check**: All principles remain satisfied. The
risk-tiered approval model (low-risk auto-apply, high-risk approval)
adds a new write path but both paths go through the same snapshot +
idempotency + logging pipeline.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-orchestrator/
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
├── __init__.py
├── main.py                  # FastAPI app factory + lifespan
├── config.py                # pydantic-settings (env vars)
├── celery_app.py            # Celery singleton
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── notes.py         # GET /notes/{path}, GET /notes/folder/{path}
│       ├── patches.py       # POST /patches, approve/reject
│       ├── commands.py      # GET/POST /commands
│       ├── jobs.py          # POST /jobs, GET /jobs/{id}, cancel
│       ├── ai.py            # POST /ai/analyze, POST /ai/chat
│       ├── logs.py          # GET /logs
│       └── health.py        # GET /health
├── models/
│   ├── __init__.py
│   ├── job.py               # Job SQLAlchemy model
│   ├── patch_operation.py   # PatchOperation model
│   ├── operation_log.py     # OperationLog model
│   └── llm_interaction.py   # LLMInteraction model
├── schemas/
│   ├── __init__.py
│   ├── note.py              # Note response schemas
│   ├── patch.py             # Patch request/response schemas
│   ├── job.py               # Job request/response schemas
│   ├── ai.py                # AI request/response schemas
│   └── log.py               # Log response schemas
├── services/
│   ├── __init__.py
│   ├── obsidian_client.py   # httpx client for Obsidian REST API
│   ├── note_parser.py       # frontmatter + markdown-it-py parsing
│   ├── patch_engine.py      # Idempotent patch application logic
│   ├── command_service.py   # Obsidian command forwarding
│   ├── job_service.py       # Job CRUD + dedup logic
│   ├── log_service.py       # Operation log writes + retention purge
│   ├── llm_provider.py      # Abstract LLM interface (Claude/OpenAI)
│   └── ai_service.py        # AI analysis, suggestions, chat
├── tasks/
│   ├── __init__.py
│   ├── vault_scan.py        # Celery task: vault scan with progress
│   ├── vault_cleanup.py     # Celery task: cleanup with risk tiers
│   ├── ai_analysis.py       # Celery task: LLM-powered analysis
│   └── log_purge.py         # Celery beat: scheduled log retention
└── db/
    ├── __init__.py
    ├── session.py            # SQLAlchemy async session factory
    └── migrations/           # Alembic migrations

tests/
├── conftest.py               # Shared fixtures
├── unit/
│   ├── test_note_parser.py
│   ├── test_patch_engine.py
│   └── test_idempotency.py   # Constitution: run twice, same result
├── integration/
│   ├── test_obsidian_client.py
│   ├── test_job_lifecycle.py
│   └── test_patch_flow.py
└── contract/
    └── test_api_contract.py

docker-compose.yml
Dockerfile
.env.example
pyproject.toml
alembic.ini
```

**Structure Decision**: Single-project layout (no frontend/backend
split). FastAPI's built-in Swagger UI serves as the monitoring
interface, eliminating the need for a separate frontend.

## Complexity Tracking

| Aspect | Justification |
|--------|---------------|
| PostgreSQL + Redis (two data stores) | Redis is required as Celery broker. Postgres provides persistent queryable storage for jobs/logs. Using Redis alone would lose audit history on restart. |
| Celery (vs simple background threads) | Celery provides task progress tracking, deduplication, scheduled beats (log purge), and can scale workers independently. Background threads cannot survive process restart or report progress externally. |
| LLM provider abstraction | User requires both Claude and OpenAI support. A simple interface with two implementations is minimal complexity for this requirement. |
