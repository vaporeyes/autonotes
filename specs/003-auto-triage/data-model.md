# Data Model: Auto-Triage for Vault Notes

**Date**: 2026-03-12
**Feature Branch**: `003-auto-triage`

## Entities

### FolderConvention (new table: `folder_conventions`)

A set of rules defining what a "complete" note looks like in a given
vault folder. Managed via CRUD API.

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| folder_path | string(1024) | Vault-relative folder path (e.g., "projects/", "meetings/") |
| required_frontmatter | json | List of {key: string, default_value: any or null}. Fields the note must have. |
| expected_tags | json | List of strings. Tags every note in this folder should have. |
| backlink_targets | json | List of folder path strings. Note must contain at least one [[link]] to a note in each target folder. |
| created_at | datetime | Convention creation timestamp (UTC) |
| updated_at | datetime | Last modification timestamp (UTC) |

**Constraints**:
- `folder_path` has a unique index (one convention per folder)
- No self-referencing FK for inheritance; inheritance is resolved at
  query time via prefix matching on folder_path (see research.md)

### TriageIssue (new table: `triage_issues`)

A detected deviation from a folder convention, produced during a triage
scan. Tracks whether the issue was auto-fixed, queued for approval, or
previously rejected.

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| job_id | uuid | FK to Job that produced this issue (the triage scan) |
| convention_id | uuid | FK to FolderConvention that was violated |
| note_path | string(1024) | Vault-relative path of the non-compliant note |
| issue_type | enum | One of: missing_frontmatter, missing_tag, missing_backlink, tag_normalization |
| risk_level | enum | Reuses existing risk_level_enum: low, high |
| suggested_fix | json | Payload describing the fix (matches patch_engine format) |
| resolution | enum | One of: auto_applied, pending_approval, rejected, superseded |
| patch_operation_id | uuid or null | FK to PatchOperation if a patch was created |
| rejected_hash | string(64) or null | Hash of (note_path, issue_type, fix payload) when rejected, for suppression |
| rejected_at | datetime or null | Timestamp of rejection, for comparison against note modification time |
| created_at | datetime | Issue detection timestamp (UTC) |

**Constraints**:
- `job_id` + `note_path` + `issue_type` + `suggested_fix` should be
  effectively unique per scan (enforced by idempotency_key on
  PatchOperation, not a DB constraint here)
- `job_id` indexed for scan result queries
- `note_path` + `issue_type` indexed for rejection lookups
- `rejected_hash` indexed for fast suppression checks

### Job (existing table: modified)

**Modification**: Add `triage_scan` to the `job_type_enum`.

The existing Job model handles all lifecycle tracking. Triage scan jobs
use the same fields:
- `target_path`: scan scope (folder path or "/" for full vault)
- `parameters`: `{"scan_type": "triage"}`
- `idempotency_key`: hash of (target_path + "triage_scan")
- `result`: summary counts (issues_found, fixes_applied, suggestions_queued)

## Relationships

```
Job 1--* TriageIssue          (each triage scan produces zero or more issues)
FolderConvention 1--* TriageIssue  (each issue references the violated convention)
TriageIssue *--0..1 PatchOperation (issue may produce a patch, or not)
```

TriageIssue references existing tables (Job, PatchOperation) and the new
FolderConvention table. PatchOperation already has the job_id FK to Job.

## Issue Type Enum

| Value | Risk Level | Description |
|-------|-----------|-------------|
| missing_frontmatter | low | Required frontmatter field absent; default value available |
| missing_tag | low | Convention-defined expected tag not present on note |
| tag_normalization | low | Tag exists but with wrong casing |
| missing_backlink | high | No link to any note in the required target folder |

## Indexes

- `folder_conventions.folder_path` -- unique index (one convention per folder)
- `triage_issues.job_id` -- for fetching all issues from a scan
- `triage_issues.note_path, issue_type` -- composite index for rejection lookups
- `triage_issues.rejected_hash` -- for fast suppression checks during scans

## Migration Notes

- Add `triage_scan` value to the existing `job_type_enum` type via
  `ALTER TYPE job_type_enum ADD VALUE 'triage_scan'`
- Add `issue_type_enum` with values: missing_frontmatter, missing_tag,
  missing_backlink, tag_normalization
- Add `triage_resolution_enum` with values: auto_applied,
  pending_approval, rejected, superseded
- Create `folder_conventions` table
- Create `triage_issues` table with FKs to jobs, folder_conventions,
  and patch_operations
- Single Alembic migration using raw SQL for enum creation (matching
  existing pattern from initial schema migration)
