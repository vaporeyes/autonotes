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

   Required variables:
   ```
   OBSIDIAN_API_KEY=your-obsidian-rest-api-key
   OBSIDIAN_API_URL=https://host.docker.internal:27124
   LLM_PROVIDER=claude
   LLM_API_KEY=your-anthropic-or-openai-key
   POSTGRES_USER=autonotes
   POSTGRES_PASSWORD=autonotes
   POSTGRES_DB=autonotes
   LOG_RETENTION_DAYS=90
   ```

3. Start the stack:
   ```bash
   docker compose up -d
   ```

4. Verify all services are healthy:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

   Expected: `{"status": "healthy", "obsidian_api": "connected", ...}`

## Usage

### Read a note
```bash
curl http://localhost:8000/api/v1/notes/Notes/daily.md
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
# Returns patch_id with status "pending_approval"

curl -X POST http://localhost:8000/api/v1/patches/<patch_id>/approve
```

### Start a vault scan
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type": "vault_scan",
       "target_path": "Notes/",
       "parameters": {"scan_type": "missing_backlinks"}}'
# Returns job_id

curl http://localhost:8000/api/v1/jobs/<job_id>
# Returns progress: {"current": 45, "total": 100}
```

### Ask the AI about your vault
```bash
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Which notes mention the Q1 review?",
       "scope": "Notes/"}'
```

### Trigger vault cleanup
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type": "vault_cleanup", "target_path": "/"}'
```

### View operation logs
```bash
curl "http://localhost:8000/api/v1/logs?since=2026-03-01&limit=50"
```

## Monitoring UI

Open `http://localhost:8000/docs` in a browser for the Swagger/Redoc
interface. This provides:
- Interactive API explorer for all endpoints
- Job submission and status tracking
- Operation log viewing with filters

## Stopping

```bash
docker compose down
```

To also remove persistent data (database):
```bash
docker compose down -v
```

## Validation Checklist

- [ ] `GET /health` returns all services connected
- [ ] `GET /notes/<path>` returns parsed frontmatter and tags
- [ ] `POST /patches` with `add_tag` auto-applies and logs the change
- [ ] `POST /patches` with `add_backlink` returns `pending_approval`
- [ ] Running the same patch twice returns `no_op` (idempotency)
- [ ] `POST /jobs` with `vault_scan` returns progress updates
- [ ] `POST /jobs` with duplicate scan returns existing job ID
- [ ] `POST /ai/chat` returns an answer grounded in vault notes
- [ ] `GET /logs` shows all operations with timestamps
