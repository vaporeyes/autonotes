# Quickstart: AI Orchestrator

**Date**: 2026-03-12
**Feature Branch**: `001-ai-orchestrator`

## Prerequisites

1. **Obsidian** installed with a vault open
2. **Obsidian Local REST API** plugin installed and enabled
   - Note the API key from plugin settings
   - Default HTTPS port: 27124
3. **Docker** and **Docker Compose** installed
4. **LLM API key** (Anthropic or OpenAI)

## Setup

1. Clone the repository and navigate to the project root:
   ```bash
   git clone <repo-url> && cd autonotes
   ```

2. Copy the environment template and fill in your keys:
   ```bash
   cp .env.example .env
   ```

   Required variables to edit:
   ```
   OBSIDIAN_API_KEY=your-obsidian-rest-api-key
   LLM_API_KEY=your-anthropic-or-openai-key
   ```

   Optional (defaults are fine for local dev):
   ```
   OBSIDIAN_API_URL=https://host.docker.internal:27124
   LLM_PROVIDER=claude
   POSTGRES_USER=autonotes
   POSTGRES_PASSWORD=autonotes
   POSTGRES_DB=autonotes
   DATABASE_URL=postgresql+asyncpg://autonotes:autonotes@postgres:5432/autonotes
   REDIS_URL=redis://redis:6379/0
   CELERY_RESULT_BACKEND=redis://redis:6379/1
   LOG_RETENTION_DAYS=90
   ```

3. Start the stack:
   ```bash
   docker compose up -d
   ```

4. Run database migrations:
   ```bash
   docker compose exec api uv run alembic upgrade head
   ```

5. Verify all services are healthy:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

   Expected: `{"status": "healthy", "obsidian_api": "connected", "redis": "connected", "postgres": "connected", "active_jobs": 0}`

## Usage

### Read a note
```bash
curl http://localhost:8000/api/v1/notes/Notes/daily.md
```

Returns parsed frontmatter, headings, tags, backlinks, word count, and content hash.

### List notes in a folder
```bash
curl "http://localhost:8000/api/v1/notes/folder/Notes?recursive=false"
```

### Add a tag (low-risk, auto-applied)
```bash
curl -X POST http://localhost:8000/api/v1/patches \
  -H "Content-Type: application/json" \
  -d '{"target_path": "Notes/daily.md",
       "operations": [{"type": "add_tag", "payload": {"tag": "reviewed"}}]}'
```

### Add a backlink (high-risk, requires approval)
```bash
curl -X POST http://localhost:8000/api/v1/patches \
  -H "Content-Type: application/json" \
  -d '{"target_path": "Notes/daily.md",
       "operations": [{"type": "add_backlink",
                        "payload": {"target": "ProjectNotes"}}]}'
# Response includes patch_id with status "pending_approval"

# Approve the patch
curl -X POST http://localhost:8000/api/v1/patches/<patch_id>/approve

# Or reject it
curl -X POST http://localhost:8000/api/v1/patches/<patch_id>/reject
```

### Update frontmatter (low-risk, auto-applied)
```bash
curl -X POST http://localhost:8000/api/v1/patches \
  -H "Content-Type: application/json" \
  -d '{"target_path": "Notes/daily.md",
       "operations": [{"type": "update_frontmatter_key",
                        "payload": {"key": "status", "value": "reviewed"}}]}'
```

### Execute an Obsidian command
```bash
# List available commands
curl http://localhost:8000/api/v1/commands

# Execute one
curl -X POST http://localhost:8000/api/v1/commands/daily-notes
```

### Start a vault scan
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type": "vault_scan",
       "target_path": "Notes/",
       "parameters": {"scan_type": "missing_backlinks"}}'
# Returns job_id

# Poll for progress
curl http://localhost:8000/api/v1/jobs/<job_id>
# Returns progress: {"current": 45, "total": 100}
```

### Trigger vault cleanup
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type": "vault_cleanup", "target_path": "/"}'
```

Cleanup auto-applies low-risk fixes (e.g., adding missing `tags` frontmatter key) and creates `pending_approval` patches for high-risk fixes.

### Ask the AI about your vault
```bash
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Which notes mention the Q1 review?",
       "scope": "Notes/"}'
```

### Request AI analysis
```bash
curl -X POST http://localhost:8000/api/v1/ai/analyze \
  -H "Content-Type: application/json" \
  -d '{"target_path": "Notes/",
       "analysis_type": "suggest_backlinks"}'
# Returns a job_id (runs in background)

# Check results
curl http://localhost:8000/api/v1/jobs/<job_id>
```

Analysis types: `suggest_backlinks`, `suggest_tags`, `generate_summary`, `cleanup_targets`

### View operation logs
```bash
curl "http://localhost:8000/api/v1/logs?since=2026-03-01&limit=50"

# Filter by target
curl "http://localhost:8000/api/v1/logs?target_path=Notes/daily.md"

# Filter by status
curl "http://localhost:8000/api/v1/logs?status=success"
```

## Monitoring UI

Open `http://localhost:8000/docs` in a browser for the Swagger UI.
Open `http://localhost:8000/redoc` for the ReDoc alternative.

The Swagger UI provides:
- Interactive API explorer for all 15 endpoints
- Job submission and status tracking
- Operation log viewing with filters
- Grouped by resource: Notes, Patches, Commands, Jobs, AI, Logs, Health

## Stopping

```bash
docker compose down
```

To also remove persistent data (database volumes):
```bash
docker compose down -v
```

## Validation Checklist

- [ ] `GET /health` returns all services connected
- [ ] `GET /notes/<path>` returns parsed frontmatter and tags
- [ ] `GET /notes/folder/<path>` returns note summaries
- [ ] `POST /patches` with `add_tag` auto-applies and logs the change
- [ ] `POST /patches` with `add_backlink` returns `pending_approval`
- [ ] `POST /patches/<id>/approve` applies the pending patch
- [ ] Running the same patch twice returns `no_op` (idempotency)
- [ ] `POST /jobs` with `vault_scan` returns progress updates
- [ ] `POST /jobs` with duplicate scan returns existing job ID
- [ ] `POST /ai/chat` returns an answer grounded in vault notes
- [ ] `POST /ai/analyze` creates a background job
- [ ] `GET /logs` shows all operations with timestamps
- [ ] Swagger UI at `/docs` groups endpoints by tag
