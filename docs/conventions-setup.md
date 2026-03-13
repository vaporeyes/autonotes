# Folder Conventions Setup

Run these commands against `http://localhost:8000/api/v1/conventions` to set up triage rules.

## 1. Projects — require status field

Notes in `40 Projects/` should track whether they're active, on hold, or done.
Missing `status` will auto-populate with `active`.

```bash
curl -X POST http://localhost:8000/api/v1/conventions \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "40 Projects/",
    "required_frontmatter": [
      {"key": "status", "default": "active"}
    ],
    "expected_tags": [],
    "backlink_targets": []
  }'
```

## 2. Permanent notes — should be tagged

Notes in `20 Permanent/` are your knowledge base. Untagged notes are hard to discover.
No default provided — this will flag untagged notes as issues but won't auto-apply
(no way to guess the right tag).

```bash
curl -X POST http://localhost:8000/api/v1/conventions \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "20 Permanent/",
    "required_frontmatter": [
      {"key": "tags"}
    ],
    "expected_tags": [],
    "backlink_targets": []
  }'
```

## 3. Recipes — enforce structured schema

Recipe notes already have a rich schema. This convention enforces it so new recipes
don't skip required fields. `category` defaults to `misc` if missing.

```bash
curl -X POST http://localhost:8000/api/v1/conventions \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "20 Permanent/Recipes/",
    "required_frontmatter": [
      {"key": "recipe"},
      {"key": "category", "default": "misc"}
    ],
    "expected_tags": ["recipe"],
    "backlink_targets": []
  }'
```

## 4. Fitness tracking — maintain consistent schema

Workout tracking notes should always have `title`, `year`, `month`, and the `fitness` tag.

```bash
curl -X POST http://localhost:8000/api/v1/conventions \
  -H 'Content-Type: application/json' \
  -d '{
    "folder_path": "20 Permanent/hobbies/Fitness/",
    "required_frontmatter": [
      {"key": "title"},
      {"key": "year"},
      {"key": "month"}
    ],
    "expected_tags": ["fitness"],
    "backlink_targets": []
  }'
```

## Verify

After creating all conventions, confirm they're registered:

```bash
curl -s http://localhost:8000/api/v1/conventions | jq
```

Test inheritance resolution for a recipe note:

```bash
curl -s "http://localhost:8000/api/v1/conventions/resolve?note_path=20 Permanent/Recipes/breakfast/huevos-rancheros.md" | jq
```

This should return merged rules from both `20 Permanent/` (requires `tags` field)
and `20 Permanent/Recipes/` (requires `recipe`, `category`; expects `recipe` tag).

## Run a triage scan

After conventions are in place:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"job_type": "triage_scan", "target_path": "/"}'
```

Check results:

```bash
curl -s http://localhost:8000/api/v1/jobs/{job_id} | jq
curl -s http://localhost:8000/api/v1/triage/results/{job_id} | jq
```
