# API Contract: Auto-Triage for Vault Notes

**Date**: 2026-03-12
**Feature Branch**: `003-auto-triage`
**Base URL**: `http://localhost:8000/api/v1`

## New Endpoints

All endpoints extend the existing API. Authentication: none (inherits
single-user localhost model from 001).

### Folder Conventions CRUD

#### POST /conventions

Create a folder convention.

**Request body**:
```json
{
  "folder_path": "projects/",
  "required_frontmatter": [
    {"key": "status", "default_value": "draft"},
    {"key": "priority", "default_value": null}
  ],
  "expected_tags": ["project"],
  "backlink_targets": []
}
```

**Response 201**:
```json
{
  "id": "uuid-conv-1",
  "folder_path": "projects/",
  "required_frontmatter": [
    {"key": "status", "default_value": "draft"},
    {"key": "priority", "default_value": null}
  ],
  "expected_tags": ["project"],
  "backlink_targets": [],
  "created_at": "2026-03-12T14:00:00Z",
  "updated_at": "2026-03-12T14:00:00Z"
}
```

**Response 409**: `{"detail": "Convention already exists for folder: projects/"}`

#### GET /conventions

List all folder conventions.

**Response 200**:
```json
{
  "conventions": [
    {
      "id": "uuid-conv-1",
      "folder_path": "projects/",
      "required_frontmatter": [...],
      "expected_tags": ["project"],
      "backlink_targets": [],
      "created_at": "2026-03-12T14:00:00Z",
      "updated_at": "2026-03-12T14:00:00Z"
    }
  ]
}
```

#### GET /conventions/{convention_id}

Retrieve a single convention by ID.

**Response 200**: Same shape as single convention above.

**Response 404**: `{"detail": "Convention not found: uuid-conv-1"}`

#### GET /conventions/resolve?path={note_path}

Resolve the merged convention for a given note path (applies inheritance).

**Query params**: `path` (string, required) -- vault-relative note path

**Response 200**:
```json
{
  "note_path": "projects/active/sprint-1.md",
  "merged_from": ["projects/", "projects/active/"],
  "required_frontmatter": [
    {"key": "status", "default_value": "draft"},
    {"key": "sprint", "default_value": null}
  ],
  "expected_tags": ["project", "active"],
  "backlink_targets": []
}
```

**Response 200** (no conventions apply):
```json
{
  "note_path": "random/note.md",
  "merged_from": [],
  "required_frontmatter": [],
  "expected_tags": [],
  "backlink_targets": []
}
```

#### PUT /conventions/{convention_id}

Update an existing convention (full replacement of rule fields).

**Request body**: Same shape as POST.

**Response 200**: Updated convention.

**Response 404**: `{"detail": "Convention not found: uuid-conv-1"}`

#### DELETE /conventions/{convention_id}

Delete a convention.

**Response 204**: No content.

**Response 404**: `{"detail": "Convention not found: uuid-conv-1"}`

### Triage Scan

#### POST /jobs

Submit a triage scan job (uses existing jobs endpoint).

**Request body**:
```json
{
  "job_type": "triage_scan",
  "target_path": "projects/",
  "parameters": {}
}
```

**Response 201** (new job):
```json
{
  "job_id": "uuid-job-1",
  "status": "pending",
  "created_at": "2026-03-12T15:00:00Z"
}
```

**Response 200** (duplicate detected):
```json
{
  "job_id": "uuid-existing",
  "status": "running",
  "message": "Identical job already in progress"
}
```

Job progress tracked via existing `GET /jobs/{job_id}` endpoint.

### Triage Results

#### GET /triage/results/{job_id}

Retrieve triage scan results for a completed job.

**Path params**: `job_id` -- UUID of the triage scan job

**Response 200**:
```json
{
  "job_id": "uuid-job-1",
  "scan_scope": "projects/",
  "notes_scanned": 42,
  "issues_found": 8,
  "fixes_applied": 5,
  "suggestions_queued": 3,
  "issues": [
    {
      "id": "uuid-issue-1",
      "note_path": "projects/my-note.md",
      "issue_type": "missing_frontmatter",
      "risk_level": "low",
      "suggested_fix": {"key": "status", "value": "draft"},
      "resolution": "auto_applied",
      "patch_operation_id": "uuid-patch-1"
    },
    {
      "id": "uuid-issue-2",
      "note_path": "projects/other-note.md",
      "issue_type": "missing_backlink",
      "risk_level": "high",
      "suggested_fix": {"target": "projects/index"},
      "resolution": "pending_approval",
      "patch_operation_id": "uuid-patch-2"
    }
  ],
  "created_at": "2026-03-12T15:01:00Z"
}
```

**Response 404**: `{"detail": "No triage results found for job uuid-job-1"}`

#### GET /triage/history

List past triage scan summaries.

**Query params**:
- `scope` (string, optional) -- filter by scan scope
- `since` (datetime, optional, default 30 days ago)
- `limit` (int, optional, default 20)

**Response 200**:
```json
{
  "scans": [
    {
      "job_id": "uuid-job-1",
      "scan_scope": "projects/",
      "notes_scanned": 42,
      "issues_found": 8,
      "fixes_applied": 5,
      "suggestions_queued": 3,
      "created_at": "2026-03-12T15:01:00Z"
    }
  ]
}
```

### Pending Suggestions

High-risk triage suggestions are managed through the existing patch
endpoints:

- `GET /patches?status=pending_approval` -- list pending patches
  (includes triage-generated ones)
- `POST /patches/{patch_id}/approve` -- approve a triage suggestion
- `POST /patches/{patch_id}/reject` -- reject a triage suggestion
  (triggers rejection tracking in TriageIssue)

No new endpoints needed for approval/rejection workflow.

## Error Format

Follows existing error contract from 001:

```json
{
  "detail": "Human-readable error message",
  "error_code": "NOT_FOUND",
  "context": {}
}
```

Error codes used by this feature: `NOT_FOUND`, `CONFLICT`,
`VALIDATION_ERROR`.
