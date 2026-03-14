# Autonotes

AI-powered orchestrator for Obsidian vault management. Reads, analyzes, and surgically modifies Markdown notes through the Obsidian Local REST API.

## What it does

- **Read & Analyze** - Parse frontmatter, headings, tags, backlinks, and word count from any note or folder
- **Surgical Edit** - Apply idempotent patch operations (add tag, add backlink, update frontmatter key, append/prepend body) with content hash verification
- **Command Execution** - List and trigger native Obsidian commands via API
- **Background Scans** - Run vault-wide scans for orphaned links, missing tags, and structural issues via Celery task queue
- **AI Assistant** - LLM-powered analysis (suggest backlinks, suggest tags, generate summaries) and conversational vault chat
- **Vault Health Analytics** - Track orphan notes, tag distribution, backlink density, and cluster connectivity. Composite health score (0-100) with historical trends and a consolidated dashboard endpoint. Scheduled scans via Celery beat
- **Auto-Triage** - Define folder conventions (required frontmatter, expected tags, backlink targets) and periodically scan notes for compliance. Low-risk fixes (missing defaults, tag normalization) auto-apply; high-risk suggestions (backlinks) queue for approval. Convention inheritance lets sub-folders override parent rules
- **Note Similarity Engine** - Embed vault notes via OpenAI text-embedding-3-small, search for similar notes by path or free-text query, detect near-duplicate pairs, cluster related notes with HDBSCAN, and generate Map of Content (MOC) drafts linking clustered notes. Incremental re-embedding via content hash staleness detection. MOC generation goes through the patch approval workflow
- **Audit Trail** - Every mutation is logged with before/after content hashes. Logs auto-purge after configurable retention period

## Architecture

```
FastAPI API (port 8000)  <-->  Obsidian Local REST API (port 27123)
      |
Celery Worker  <-->  Redis (broker + result backend)
      |
PostgreSQL + pgvector (jobs, patches, logs, LLM interactions, conventions, triage issues, embeddings)
```

All services run in Docker Compose. The API and worker containers reach Obsidian on the host machine via `host.docker.internal`.

## Quick Start

### Prerequisites

- [Obsidian](https://obsidian.md) with the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin enabled
- [Docker](https://www.docker.com/) and Docker Compose
- An LLM API key (Anthropic or OpenAI) for AI features
- An OpenAI API key for the Note Similarity Engine (embeddings)

### Setup

```bash
# Clone and configure
git clone <repo-url> && cd autonotes
cp .env.example .env
# Edit .env with your Obsidian API key and LLM API key

# Start the stack
docker compose up -d

# Run database migrations
docker compose exec api uv run alembic upgrade head

# Verify
curl http://localhost:8000/api/v1/health
```

Open `http://localhost:8000/docs` for the Swagger UI.

See [quickstart.md](specs/001-ai-orchestrator/quickstart.md) for detailed usage examples.

## API Endpoints

| Group | Endpoints | Description |
|-------|-----------|-------------|
| Notes | `GET /notes/{path}`, `GET /notes/folder/{path}` | Read and analyze notes |
| Patches | `POST /patches`, `POST /patches/{id}/approve`, `POST /patches/{id}/reject` | Surgical edits with risk-tiered approval |
| Commands | `GET /commands`, `POST /commands/{id}` | Obsidian command execution |
| Jobs | `POST /jobs`, `GET /jobs/{id}`, `GET /jobs`, `POST /jobs/{id}/cancel` | Background task management |
| AI | `POST /ai/analyze`, `POST /ai/chat` | LLM-powered analysis and chat |
| Conventions | `POST /conventions`, `GET /conventions`, `GET /conventions/{id}`, `PUT /conventions/{id}`, `DELETE /conventions/{id}`, `GET /conventions/resolve` | Folder convention CRUD and inheritance resolution |
| Triage | `GET /triage/results/{job_id}`, `GET /triage/history` | Auto-triage scan results and history |
| Similarity | `POST /similarity/search`, `GET /similarity/duplicates/{job_id}` | Note similarity search and duplicate detection |
| Clusters | `GET /clusters/latest`, `GET /clusters/{id}`, `POST /clusters/{id}/moc` | Topic clusters and MOC generation |
| Embeddings | `GET /embeddings/status` | Embedding index coverage |
| Vault Health | `GET /vault-health/snapshot/{job_id}`, `GET /vault-health/latest`, `GET /vault-health/trends`, `GET /vault-health/dashboard` | Health metrics, trends, dashboard |
| Logs | `GET /logs` | Operation audit trail |
| Health | `GET /health` | Service connectivity check |

All endpoints are under `/api/v1`. Embedding and clustering are triggered via `POST /jobs` with `job_type: "embed_notes"` or `"cluster_notes"`. See [contracts/api.md](specs/001-ai-orchestrator/contracts/api.md) for the orchestrator API spec, [contracts/api.md](specs/002-vault-health-analytics/contracts/api.md) for health analytics, [contracts/api.md](specs/003-auto-triage/contracts/api.md) for auto-triage, and [contracts/api.md](specs/004-note-similarity-engine/contracts/api.md) for similarity engine.

## Key Design Decisions

- **Risk-tiered approval**: Low-risk ops (add/remove tag, update frontmatter key) auto-apply. High-risk ops (backlinks, body modifications) require explicit approval.
- **Three-layer idempotency**: DB idempotency key, deterministic Celery task ID, check-before-write guards in the patch engine.
- **Local-first privacy**: No note content leaves the network except during explicit AI operations. Every LLM call is logged with the note paths sent and token counts.
- **Surgical updates**: Frontmatter edits via key-level merge (python-frontmatter + ruamel.yaml). Body edits via line-range splice using markdown-it-py `.map` offsets. No full-file rewrites.

## Development

```bash
# Install dependencies locally
uv sync

# Run the API (requires running Postgres + Redis)
uv run uvicorn app.main:app --reload

# Run the Celery worker
uv run celery -A app.celery_app worker --loglevel=info

# Lint
uv run ruff check .
```

## Stack

- Python 3.12, FastAPI, Celery, httpx
- PostgreSQL 16 + pgvector, Redis 7
- python-frontmatter + ruamel.yaml (frontmatter parsing)
- markdown-it-py (Markdown AST with line offsets)
- Anthropic SDK / OpenAI SDK (LLM + embeddings)
- numpy, scikit-learn (clustering, similarity)
- SQLAlchemy + Alembic (async ORM + migrations)
- Docker Compose (deployment)
