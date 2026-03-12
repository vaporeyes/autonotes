# API Contract: AI Orchestrator

**Date**: 2026-03-12
**Feature Branch**: `001-ai-orchestrator`
**Base URL**: `http://localhost:8000/api/v1`

## Authentication

No authentication for v1 (single-user, localhost-only). The Obsidian
REST API key is configured server-side via environment variable.

## Endpoints

### Notes

#### GET /notes/{path:path}

Read and analyze a single note.

**Path params**: `path` -- vault-relative file path (e.g., `Notes/daily.md`)

**Response 200**:
```json
{
  "file_path": "Notes/daily.md",
  "frontmatter": {"tags": ["daily"], "date": "2026-03-12"},
  "headings": [{"level": 1, "text": "Daily Note", "line": 3}],
  "tags": ["daily"],
  "backlinks": ["ProjectNotes", "WeeklyReview"],
  "word_count": 342,
  "last_modified": "2026-03-12T10:30:00Z",
  "content_hash": "sha256:abc123..."
}
```

**Response 404**: `{"detail": "Note not found: Notes/daily.md"}`

#### GET /notes/folder/{path:path}

Analyze all notes in a folder.

**Path params**: `path` -- vault-relative folder path

**Query params**: `recursive` (bool, default false)

**Response 200**:
```json
{
  "folder": "Notes/",
  "note_count": 10,
  "notes": [
    {
      "file_path": "Notes/daily.md",
      "title": "Daily Note",
      "tags": ["daily"],
      "backlink_count": 2,
      "word_count": 342,
      "last_modified": "2026-03-12T10:30:00Z"
    }
  ]
}
```

### Patch Operations

#### POST /patches

Submit one or more patch operations for a note.

**Request body**:
```json
{
  "target_path": "Notes/daily.md",
  "operations": [
    {"type": "add_tag", "payload": {"tag": "archived"}},
    {"type": "add_backlink", "payload": {"target": "ProjectNotes"}}
  ]
}
```

**Response 200** (all applied):
```json
{
  "target_path": "Notes/daily.md",
  "results": [
    {"type": "add_tag", "status": "applied", "tag": "archived"},
    {"type": "add_backlink", "status": "pending_approval",
     "reason": "high-risk operation requires approval"}
  ],
  "job_id": "uuid-123"
}
```

**Response 409**: Content hash conflict (note was modified externally).

#### POST /patches/{patch_id}/approve

Approve a high-risk patch operation.

**Response 200**: `{"status": "applied", "after_hash": "sha256:..."}`
**Response 404**: Patch not found.
**Response 409**: Note content changed since patch was created.

#### POST /patches/{patch_id}/reject

Reject a high-risk patch operation.

**Response 200**: `{"status": "skipped"}`

### Commands

#### GET /commands

List available Obsidian commands.

**Response 200**:
```json
{
  "commands": [
    {"id": "editor:toggle-bold", "name": "Toggle bold"},
    {"id": "daily-notes", "name": "Open daily note"}
  ]
}
```

#### POST /commands/{command_id}

Execute an Obsidian command.

**Response 200**: `{"command_id": "daily-notes", "status": "executed"}`
**Response 404**: `{"detail": "Unknown command: bad-command"}`
**Response 502**: `{"detail": "Obsidian REST API unreachable"}`

### Jobs

#### POST /jobs

Submit a background job.

**Request body**:
```json
{
  "job_type": "vault_scan",
  "target_path": "Notes/",
  "parameters": {"scan_type": "missing_backlinks"}
}
```

**Response 201** (new job):
```json
{
  "job_id": "uuid-456",
  "status": "pending",
  "created_at": "2026-03-12T10:30:00Z"
}
```

**Response 200** (existing duplicate):
```json
{
  "job_id": "uuid-existing",
  "status": "running",
  "message": "Identical job already in progress"
}
```

#### GET /jobs/{job_id}

Get job status and progress.

**Response 200**:
```json
{
  "job_id": "uuid-456",
  "job_type": "vault_scan",
  "status": "running",
  "progress": {"current": 45, "total": 100},
  "created_at": "2026-03-12T10:30:00Z",
  "started_at": "2026-03-12T10:30:01Z"
}
```

#### GET /jobs

List jobs with filtering.

**Query params**: `status` (enum), `job_type` (enum), `since` (datetime), `limit` (int, default 50)

**Response 200**: `{"jobs": [...], "total": 150}`

#### POST /jobs/{job_id}/cancel

Cancel a pending or running job.

**Response 200**: `{"status": "cancelled"}`

### AI Operations

#### POST /ai/analyze

Analyze a note or folder using the LLM. Returns suggestions.

**Request body**:
```json
{
  "target_path": "Notes/daily.md",
  "analysis_type": "suggest_backlinks"
}
```

`analysis_type` values: `suggest_backlinks`, `suggest_tags`,
`generate_summary`, `cleanup_targets`

**Response 201**: Returns a job ID (analysis runs as background task).

#### POST /ai/chat

Ask a question about vault content.

**Request body**:
```json
{
  "question": "Which notes mention the Q1 review?",
  "scope": "Notes/"
}
```

**Response 200**:
```json
{
  "answer": "3 notes mention Q1 review: ...",
  "sources": ["Notes/q1-review.md", "Notes/meeting-jan.md"],
  "llm_provider": "claude",
  "notes_sent": ["Notes/q1-review.md", "Notes/meeting-jan.md"]
}
```

### Monitoring

#### GET /logs

Query operation logs.

**Query params**: `target_path` (string), `operation_name` (string),
`status` (enum), `since` (datetime), `until` (datetime),
`limit` (int, default 100)

**Response 200**: `{"logs": [...], "total": 500}`

#### GET /health

System health check.

**Response 200**:
```json
{
  "status": "healthy",
  "obsidian_api": "connected",
  "redis": "connected",
  "postgres": "connected",
  "active_jobs": 2
}
```

## Error Format

All errors follow a consistent structure:

```json
{
  "detail": "Human-readable error message",
  "error_code": "CONFLICT",
  "context": {"target_path": "Notes/daily.md", "expected_hash": "..."}
}
```

Standard error codes: `NOT_FOUND`, `CONFLICT`, `OBSIDIAN_UNREACHABLE`,
`OBSIDIAN_ERROR`, `VALIDATION_ERROR`, `LLM_ERROR`.
