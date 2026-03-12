# Data Model: AI Orchestrator

**Date**: 2026-03-12
**Feature Branch**: `001-ai-orchestrator`

## Entities

### Note (read-only representation, not persisted)

Represents a parsed Obsidian vault file. Not stored in the database;
constructed on-demand from the Obsidian REST API response.

| Field | Type | Description |
|-------|------|-------------|
| file_path | string | Vault-relative path (e.g., `Notes/daily.md`) |
| frontmatter | dict | Parsed YAML key-value metadata |
| body | string | Raw markdown body (after frontmatter) |
| tags | list[string] | Extracted tags (from frontmatter + inline #tags) |
| backlinks | list[string] | Extracted wikilinks (`[[target]]`) |
| headings | list[Heading] | Parsed heading tree (level, text, line range) |
| word_count | int | Word count of body content |
| last_modified | datetime | File mtime from Obsidian API stat |
| content_hash | string | SHA-256 of raw file content (for conflict detection) |

### PatchOperation

A targeted modification request. Persisted in PostgreSQL as part of
the job record for audit trail.

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| job_id | uuid | FK to Job that created this operation |
| target_path | string | Vault-relative note path |
| operation_type | enum | `add_tag`, `remove_tag`, `add_backlink`, `remove_backlink`, `update_frontmatter_key`, `append_body`, `prepend_body` |
| payload | json | Operation-specific data (see below) |
| idempotency_key | string | Deterministic hash of (target_path + operation_type + payload) |
| risk_level | enum | `low` (auto-apply) or `high` (requires approval) |
| status | enum | `pending_approval`, `approved`, `applied`, `skipped`, `failed` |
| before_hash | string | Content hash before application (null if not yet applied) |
| after_hash | string | Content hash after application (null if not yet applied) |
| created_at | datetime | When the operation was created |
| applied_at | datetime | When the operation was applied (null if pending) |

**Payload examples by operation_type**:
- `add_tag`: `{"tag": "archived"}`
- `remove_tag`: `{"tag": "draft"}`
- `add_backlink`: `{"target": "ProjectNotes", "display_text": null}`
- `update_frontmatter_key`: `{"key": "status", "value": "reviewed"}`
- `append_body`: `{"heading": "## References", "content": "- [[New]]"}`

**Risk classification**:
- Low risk (auto-apply): `add_tag`, `remove_tag`, `update_frontmatter_key`
- High risk (requires approval): `add_backlink`, `remove_backlink`, `append_body`, `prepend_body`

### Job

A trackable unit of work (scan, cleanup, AI analysis, or manual patch).

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| celery_task_id | string | Celery AsyncResult ID |
| job_type | enum | `vault_scan`, `vault_cleanup`, `ai_analysis`, `ai_chat`, `manual_patch`, `batch_patch` |
| target_path | string | Vault path or folder being operated on (null for vault-wide) |
| parameters | json | Job-specific input parameters |
| idempotency_key | string | Deterministic hash for dedup (null for non-dedup jobs like chat) |
| status | enum | `pending`, `running`, `completed`, `failed`, `cancelled` |
| progress_current | int | Notes processed so far (null for non-scan jobs) |
| progress_total | int | Total notes to process (null for non-scan jobs) |
| result | json | Job output (scan results, suggestions, chat response) |
| error_message | string | Error details if failed (null otherwise) |
| created_at | datetime | When the job was submitted |
| started_at | datetime | When execution began |
| completed_at | datetime | When execution finished |

**State transitions**:
```
pending -> running -> completed
pending -> running -> failed
pending -> cancelled
running -> cancelled
```

**Deduplication rule**: For `vault_scan` and `vault_cleanup` jobs, if a
job with the same `idempotency_key` exists in `pending` or `running`
status, the system returns the existing job ID instead of creating a
new one.

### OperationLog

Immutable audit record for every vault mutation.

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| job_id | uuid | FK to Job (null for ad-hoc operations) |
| patch_operation_id | uuid | FK to PatchOperation (null for command executions) |
| operation_name | string | Human-readable name (e.g., "add_tag:archived") |
| target_path | string | Vault-relative note path |
| before_hash | string | Content hash before mutation |
| after_hash | string | Content hash after mutation (same as before if no-op) |
| status | enum | `success`, `failure`, `no_op` |
| error_message | string | Error details if failed |
| llm_notes_sent | list[string] | Note paths sent to LLM (empty for non-AI ops) |
| created_at | datetime | Timestamp of the operation |

**Retention**: Logs older than the configured retention period (default
90 days) are purged by a scheduled cleanup task.

### LLMInteraction

Tracks content sent to external LLM providers for privacy auditing.

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| job_id | uuid | FK to Job |
| provider | string | `claude` or `openai` |
| model | string | Model identifier used |
| notes_sent | list[string] | Vault-relative paths of notes included in prompt |
| prompt_tokens | int | Token count of the prompt |
| completion_tokens | int | Token count of the response |
| created_at | datetime | When the LLM call was made |

## Relationships

```
Job 1--* PatchOperation    (a job produces zero or more patch ops)
Job 1--* OperationLog      (a job generates one or more log entries)
Job 1--* LLMInteraction    (AI jobs track LLM calls)
PatchOperation 1--1 OperationLog  (each applied patch has a log entry)
```

## Indexes

- `Job.idempotency_key` -- unique partial index where status in
  (`pending`, `running`) for dedup queries
- `Job.status` -- for filtering active/completed jobs
- `Job.created_at` -- for time-range queries in monitoring UI
- `OperationLog.target_path` -- for per-note audit history
- `OperationLog.created_at` -- for time-range filtering and retention
  purge
- `PatchOperation.idempotency_key` -- unique index for dedup
- `LLMInteraction.job_id` -- for joining with job details
