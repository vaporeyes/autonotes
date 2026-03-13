# autonotes Development Guidelines

## Project Overview

AI Orchestrator for Obsidian vault management. FastAPI API + Celery worker + PostgreSQL + Redis, deployed via Docker Compose.

## Active Technologies

- Python 3.12
- FastAPI, Celery, httpx, SQLAlchemy, Alembic
- python-frontmatter, ruamel.yaml, markdown-it-py
- Anthropic SDK, OpenAI SDK
- PostgreSQL 16 (persistent), Redis 7 (broker + cache)
- Docker Compose

## Project Structure

```text
app/
  __init__.py
  main.py              # FastAPI app factory + lifespan
  config.py            # pydantic-settings (env vars)
  celery_app.py        # Celery singleton + beat schedule
  api/routes/
    __init__.py         # Shared error handling (AppError, factory functions)
    health.py           # GET /health
    notes.py            # GET /notes/{path}, GET /notes/folder/{path}
    patches.py          # POST /patches, approve, reject
    commands.py         # GET/POST /commands
    jobs.py             # POST /jobs, GET /jobs, cancel
    ai.py               # POST /ai/analyze, POST /ai/chat
    logs.py             # GET /logs
    conventions.py      # CRUD /conventions, GET /conventions/resolve
    triage.py           # GET /triage/results, GET /triage/history
  models/
    job.py              # Job (vault_scan, cleanup, ai_analysis, triage_scan, etc.)
    patch_operation.py  # PatchOperation (add_tag, add_backlink, etc.)
    operation_log.py    # OperationLog (immutable audit)
    llm_interaction.py  # LLMInteraction (privacy tracking)
    folder_convention.py # FolderConvention (per-folder rules)
    triage_issue.py     # TriageIssue (convention violation records)
  schemas/              # Pydantic request/response models
  services/
    obsidian_client.py  # httpx async client for Obsidian REST API
    note_parser.py      # Frontmatter + markdown-it-py parsing
    patch_engine.py     # Idempotent patch application logic
    log_service.py      # Operation log writes + retention purge
    command_service.py  # Obsidian command forwarding
    job_service.py      # Job CRUD + dedup logic
    llm_provider.py     # Abstract LLM interface (Claude/OpenAI)
    ai_service.py       # AI analysis, suggestions, chat
    prompts.py          # System prompts for LLM interactions
    convention_service.py # Convention CRUD + inheritance resolution
    triage_service.py   # Triage scan engine + auto-fix + suggestions
  tasks/
    vault_scan.py       # Celery: vault scan with progress
    vault_cleanup.py    # Celery: cleanup with risk tiers
    ai_analysis.py      # Celery: LLM-powered analysis
    log_purge.py        # Celery beat: scheduled log retention
    triage_scan.py      # Celery: auto-triage scan with progress
  db/
    session.py          # SQLAlchemy async engine + session factory
    migrations/         # Alembic migrations
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

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
