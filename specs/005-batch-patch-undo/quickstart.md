# Quickstart: Batch Patch Operations & Undo/Rollback

**Prerequisites**: Stack running (`docker compose up -d`), migrations applied (`docker compose exec api uv run alembic upgrade head`).

## 1. Batch patch by folder

Add tag `#review` to all notes in `00 Fleeting/`:

```bash
curl -X POST http://localhost:8000/api/v1/batch-patches \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "00 Fleeting/",
    "operations": [{"type": "add_tag", "payload": {"tag": "review"}}]
  }' | jq
```

With recursive subfolder inclusion:

```bash
curl -X POST http://localhost:8000/api/v1/batch-patches \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "00 Fleeting/",
    "recursive": true,
    "operations": [{"type": "add_tag", "payload": {"tag": "review"}}]
  }' | jq
```

## 2. Preview before applying (dry run)

See which notes would be affected without making changes:

```bash
curl -X POST http://localhost:8000/api/v1/batch-patches \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "20 Permanent/",
    "recursive": true,
    "operations": [{"type": "add_tag", "payload": {"tag": "archived"}}],
    "dry_run": true
  }' | jq '.target_count, .results[] | {note_path, status}'
```

## 3. Batch patch by similarity query

Add tag `#kubernetes` to notes similar to "Kubernetes deployment strategies":

```bash
curl -X POST http://localhost:8000/api/v1/batch-patches \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "kubernetes deployment strategies",
    "threshold": 0.6,
    "limit": 20,
    "operations": [{"type": "add_tag", "payload": {"tag": "kubernetes"}}]
  }' | jq
```

## 4. Monitor large batch jobs

For batches exceeding 10 notes, the response returns a job ID:

```bash
curl -s http://localhost:8000/api/v1/jobs/{job_id} | jq '.status, .progress'
```

Wait for completion, then view results:

```bash
curl -s http://localhost:8000/api/v1/jobs/{job_id} | jq '.result'
```

## 5. Undo a single patch

Revert a specific patch operation:

```bash
curl -X POST http://localhost:8000/api/v1/patches/{patch_id}/undo | jq
# {"status": "reverted", "before_hash": "sha256:...", "after_hash": "sha256:..."}
```

If the note has been modified since the patch was applied, you'll get a conflict:

```bash
# 409 Conflict
# {"detail": "Note content changed since patch was applied", ...}
```

## 6. Undo an entire batch

Revert all patches from a batch job:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/undo | jq
```

View per-note undo results:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/undo | jq '.results[] | {note_path, status, reason}'
# {"note_path": "00 Fleeting/idea-1.md", "status": "reverted", "reason": null}
# {"note_path": "00 Fleeting/idea-2.md", "status": "conflict", "reason": "Note content changed since patch was applied"}
```

## 7. Verify audit trail

Check that undo operations are logged:

```bash
curl -s "http://localhost:8000/api/v1/logs?limit=10" | jq '.[] | select(.operation_name | startswith("undo:")) | {operation_name, target_path, before_hash, after_hash}'
```
