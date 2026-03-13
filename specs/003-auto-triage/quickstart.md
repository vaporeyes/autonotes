# Quickstart: Auto-Triage for Vault Notes

**Feature Branch**: `003-auto-triage`

## Prerequisites

- Running stack: `docker compose up -d`
- Database migrated: `docker compose exec api uv run alembic upgrade head`
- Obsidian with Local REST API plugin running

## 1. Define a Folder Convention

```bash
curl -X POST http://localhost:8000/api/v1/conventions \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "projects/",
    "required_frontmatter": [
      {"key": "status", "default_value": "draft"},
      {"key": "priority", "default_value": null}
    ],
    "expected_tags": ["project"],
    "backlink_targets": []
  }'
```

## 2. Run a Triage Scan

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"job_type": "triage_scan", "target_path": "projects/"}'
```

Note the `job_id` from the response.

## 3. Check Scan Progress

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

## 4. View Triage Results

```bash
curl http://localhost:8000/api/v1/triage/results/{job_id}
```

The response shows:
- **auto_applied**: Low-risk fixes already applied (missing frontmatter
  defaults, tag normalization, missing expected tags)
- **pending_approval**: High-risk suggestions awaiting review (backlink
  additions)

## 5. Approve or Reject Suggestions

```bash
# Approve a pending patch
curl -X POST http://localhost:8000/api/v1/patches/{patch_id}/approve

# Reject a pending patch
curl -X POST http://localhost:8000/api/v1/patches/{patch_id}/reject
```

## 6. View Triage History

```bash
curl http://localhost:8000/api/v1/triage/history
```

## Scheduled Scans

Triage scans run automatically on a configurable schedule. Set via
environment variable:

```
TRIAGE_SCAN_CRON=0 5 * * *    # Daily at 5am UTC (default)
TRIAGE_SCAN_SCOPE=/            # Full vault (default)
```

## Convention Inheritance Example

```bash
# Parent convention for all projects
curl -X POST http://localhost:8000/api/v1/conventions \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "projects/",
    "required_frontmatter": [{"key": "status", "default_value": "draft"}],
    "expected_tags": ["project"],
    "backlink_targets": []
  }'

# Child convention adds sprint field for active projects
curl -X POST http://localhost:8000/api/v1/conventions \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "projects/active/",
    "required_frontmatter": [{"key": "sprint", "default_value": null}],
    "expected_tags": ["active"],
    "backlink_targets": []
  }'

# Resolve merged convention for a note
curl 'http://localhost:8000/api/v1/conventions/resolve?path=projects/active/my-task.md'
```

The resolved convention merges both: requires `status` (with default
"draft") and `sprint` (no default), expects tags `project` and `active`.
