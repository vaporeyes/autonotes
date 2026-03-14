# autonotes Development Guidelines

## Project Overview

AI Orchestrator for Obsidian vault management. FastAPI API + Celery worker + PostgreSQL + Redis, deployed via Docker Compose. Includes a lightweight web dashboard at `/dashboard/`.

## Active Technologies

- Python 3.12
- FastAPI, Celery, httpx, SQLAlchemy, Alembic
- python-frontmatter, ruamel.yaml, markdown-it-py
- Anthropic SDK, OpenAI SDK (LLM + embeddings)
- numpy, scikit-learn (clustering, similarity)
- PostgreSQL 16 + pgvector (persistent), Redis 7 (broker + cache)
- Docker Compose
- Vanilla HTML/CSS/JavaScript ES6+ (web dashboard, no frameworks)

## Project Structure

```text
app/
  __init__.py
  main.py              # FastAPI app factory + lifespan + static file mount
  config.py            # pydantic-settings (env vars)
  celery_app.py        # Celery singleton + beat schedule
  api/routes/
    __init__.py         # Shared error handling (AppError, factory functions)
    health.py           # GET /health
    notes.py            # GET /notes/{path}, GET /notes/folder/{path}, GET /vault-structure
    patches.py          # GET /patches, POST /patches, approve, reject, undo
    batch_patches.py    # POST /batch-patches (folder/query batch operations)
    commands.py         # GET/POST /commands
    jobs.py             # POST /jobs, GET /jobs, cancel, undo
    ai.py               # POST /ai/analyze, POST /ai/chat
    logs.py             # GET /logs
    conventions.py      # CRUD /conventions, GET /conventions/resolve
    triage.py           # GET /triage/results, GET /triage/history
    similarity.py       # POST /similarity/search, GET /similarity/duplicates, GET /embeddings/status
    clusters.py         # GET /clusters/latest, GET /clusters/{id}, POST /clusters/{id}/moc
    vault_health.py     # GET /vault-health/snapshot, latest, trends, dashboard
  models/
    job.py              # Job (vault_scan, cleanup, ai_analysis, triage_scan, embed_notes, cluster_notes, batch_patch)
    patch_operation.py  # PatchOperation (add_tag, add_backlink, create_moc, etc.)
    operation_log.py    # OperationLog (immutable audit)
    llm_interaction.py  # LLMInteraction (privacy tracking)
    folder_convention.py # FolderConvention (per-folder rules)
    triage_issue.py     # TriageIssue (convention violation records)
    note_embedding.py   # NoteEmbedding (VECTOR(1536) via pgvector)
    note_cluster.py     # NoteCluster + ClusterMember
    duplicate_pair.py   # DuplicatePair (near-duplicate detection)
    health_snapshot.py  # HealthSnapshot (vault health analytics)
  schemas/              # Pydantic request/response models
  services/
    obsidian_client.py  # httpx async client for Obsidian REST API
    note_parser.py      # Frontmatter + markdown-it-py parsing
    patch_engine.py     # Idempotent patch application + reverse-apply for undo
    batch_patch_service.py # Batch note selection + batch apply logic
    undo_service.py     # Single and batch undo with hash verification
    log_service.py      # Operation log writes + retention purge
    command_service.py  # Obsidian command forwarding
    job_service.py      # Job CRUD + dedup logic
    llm_provider.py     # Abstract LLM interface (Claude/OpenAI)
    ai_service.py       # AI analysis, suggestions, chat
    prompts.py          # System prompts for LLM interactions
    convention_service.py # Convention CRUD + inheritance resolution
    triage_service.py   # Triage scan engine + auto-fix + suggestions
    embedding_service.py # OpenAI embedding generation + staleness detection
    similarity_service.py # pgvector cosine search + on-the-fly embedding
    cluster_service.py  # HDBSCAN clustering + duplicate detection
    moc_service.py      # MOC Markdown generation + PatchOperation creation
    health_service.py   # Vault health analytics + trend aggregation
  tasks/
    vault_scan.py       # Celery: vault scan with progress
    vault_cleanup.py    # Celery: cleanup with risk tiers
    ai_analysis.py      # Celery: LLM-powered analysis
    log_purge.py        # Celery beat: scheduled log retention
    triage_scan.py      # Celery: auto-triage scan with progress
    embedding_job.py    # Celery: vault-wide note embedding
    cluster_job.py      # Celery: HDBSCAN clustering + duplicate detection
    batch_patch_job.py  # Celery: async batch patch operations
    vault_health_scan.py # Celery: vault health scan
  db/
    session.py          # SQLAlchemy async engine + session factory
    migrations/         # Alembic migrations
  static/               # Web dashboard (vanilla HTML/CSS/JS SPA)
    index.html          # SPA shell with nav
    css/styles.css      # Dark theme
    js/app.js           # Router + shared utilities
    js/api.js           # API client (fetch wrappers)
    js/views/           # One JS file per view (dashboard, notes, patches, jobs, chat, logs)
    js/components/      # Shared components (sparkline, progress-bar, folder-tree)
```

## Commands

```bash
# Run full stack
docker compose up -d
docker compose exec api uv run alembic upgrade head

# Development (local)
uv sync
uv run uvicorn app.main:app --reload
uv run celery -A app.celery_app worker --loglevel=info

# Lint
uv run ruff check .

# Test
uv run pytest
```

## Code Conventions

- All Python files start with two `# ABOUTME:` comment lines
- pydantic-settings for config (`app/config.py`)
- Async SQLAlchemy sessions via `get_session` FastAPI dependency
- All write operations go through `patch_engine.py` for idempotency
- All mutations logged via `log_service.py`
- Error responses use `AppError` from `app/api/routes/__init__.py`
- Obsidian REST API PATCH uses heading-based headers, NOT JSON Patch RFC 6902

## Key Architecture Rules

- No full-file rewrites. Frontmatter: key-level merge. Body: line-range splice.
- Low-risk ops auto-apply. High-risk ops require approval.
- No note content sent to LLM without explicit user trigger.
- Jobs with same idempotency_key deduplicate against pending/running jobs.
