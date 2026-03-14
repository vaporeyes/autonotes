# API Contract: Batch Patch Operations & Undo/Rollback

Base path: `/api/v1`

---

## Batch Patch Operations

### POST /batch-patches

Apply one or more operations to multiple notes selected by folder path or similarity query.

**Request Body**:

```json
{
  "folder_path": "00 Fleeting/",
  "recursive": true,
  "operations": [
    {"type": "add_tag", "payload": {"tag": "review"}}
  ],
  "dry_run": false
}
```

Or with similarity query:

```json
{
  "query": "kubernetes deployment strategies",
  "threshold": 0.6,
  "limit": 20,
  "operations": [
    {"type": "add_tag", "payload": {"tag": "kubernetes"}}
  ],
  "dry_run": false
}
```

**Validation**:
- Exactly one of `folder_path` or `query` must be provided.
- `operations` must contain at least one operation.
- `threshold` defaults to 0.5, only used with `query`.
- `limit` is optional, only used with `query`.
- `recursive` defaults to false, only used with `folder_path`.
- `dry_run` defaults to false.

**Response (sync, <=10 notes)** `200 OK`:

```json
{
  "job_id": "uuid",
  "target_count": 5,
  "applied_count": 4,
  "skipped_count": 1,
  "pending_count": 0,
  "failed_count": 0,
  "dry_run": false,
  "results": [
    {
      "note_path": "00 Fleeting/idea-1.md",
      "status": "applied",
      "patch_ids": ["uuid"],
      "reason": null
    },
    {
      "note_path": "00 Fleeting/idea-2.md",
      "status": "no_op",
      "patch_ids": ["uuid"],
      "reason": "tag already exists"
    }
  ]
}
```

**Response (async, >10 notes)** `202 Accepted`:

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Batch operation queued. Monitor progress via GET /jobs/{job_id}."
}
```

The job result (available via `GET /jobs/{job_id}`) contains the same `BatchPatchResult` structure as the synchronous response.

**Dry-run response** `200 OK`:

```json
{
  "job_id": null,
  "target_count": 50,
  "applied_count": 0,
  "skipped_count": 0,
  "pending_count": 0,
  "failed_count": 0,
  "dry_run": true,
  "results": [
    {
      "note_path": "00 Fleeting/idea-1.md",
      "status": "would_apply",
      "patch_ids": [],
      "reason": null
    },
    {
      "note_path": "00 Fleeting/idea-2.md",
      "status": "would_skip",
      "patch_ids": [],
      "reason": "tag already exists"
    }
  ]
}
```

**Error Responses**:
- `404 Not Found`: Folder path does not exist.
- `422 Unprocessable Entity`: Both or neither of `folder_path`/`query` provided, or empty operations list.

---

## Undo Operations

### POST /patches/{patch_id}/undo

Undo a single applied patch operation by reverse-applying it.

**Path Parameters**:
- `patch_id` (UUID): The PatchOperation to undo.

**Response** `200 OK`:

```json
{
  "status": "reverted",
  "before_hash": "sha256:abc...",
  "after_hash": "sha256:def..."
}
```

**Error Responses**:
- `404 Not Found`: Patch not found.
- `409 Conflict`: Patch is not in `applied` status, or note content has diverged since the patch was applied.

  ```json
  {
    "detail": "Note content changed since patch was applied",
    "target_path": "path/to/note.md",
    "expected_hash": "sha256:abc...",
    "current_hash": "sha256:xyz..."
  }
  ```
- `409 Conflict`: Note has been deleted from the vault.

  ```json
  {
    "detail": "Note no longer exists in vault",
    "target_path": "path/to/note.md"
  }
  ```

---

### POST /jobs/{job_id}/undo

Undo all applied patches from a batch job.

**Path Parameters**:
- `job_id` (UUID): The Job whose patches to undo.

**Response** `200 OK`:

```json
{
  "job_id": "uuid",
  "reverted_count": 7,
  "conflict_count": 2,
  "error_count": 1,
  "results": [
    {
      "patch_id": "uuid",
      "note_path": "path/to/note.md",
      "status": "reverted",
      "reason": null
    },
    {
      "patch_id": "uuid",
      "note_path": "path/to/other.md",
      "status": "conflict",
      "reason": "Note content changed since patch was applied"
    }
  ]
}
```

**Error Responses**:
- `404 Not Found`: Job not found.
- `409 Conflict`: Job has no applied patches to undo.
