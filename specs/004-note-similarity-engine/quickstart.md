# Quickstart: Note Similarity Engine

**Prerequisites**: Stack running (`docker compose up -d`), migrations applied (`docker compose exec api uv run alembic upgrade head`).

## 1. Check embedding status

```bash
curl -s http://localhost:8000/api/v1/embeddings/status | jq
```

Expected: `total_embedded: 0`, `coverage_percent: 0`.

## 2. Run an embedding job

Embed all notes (excluding templates and attachments):

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"job_type": "embed_notes", "target_path": "/"}' | jq
```

Monitor progress:

```bash
curl -s http://localhost:8000/api/v1/jobs/{job_id} | jq '.progress'
# {"current": 250, "total": 647}
```

Wait for completion, then check coverage:

```bash
curl -s http://localhost:8000/api/v1/embeddings/status | jq
# total_embedded: 635, coverage_percent: 98.1
```

## 3. Search for similar notes

By note path:

```bash
curl -X POST http://localhost:8000/api/v1/similarity/search \
  -H 'Content-Type: application/json' \
  -d '{
    "note_path": "20 Permanent/Cloud/AWS/EC2.md",
    "threshold": 0.6,
    "limit": 10
  }' | jq
```

By free-text query:

```bash
curl -X POST http://localhost:8000/api/v1/similarity/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "kubernetes deployment strategies",
    "threshold": 0.5,
    "limit": 10
  }' | jq
```

## 4. Run clustering and duplicate detection

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "job_type": "cluster_notes",
    "parameters": {"min_cluster_size": 3, "duplicate_threshold": 0.9}
  }' | jq
```

Wait for completion, then view clusters:

```bash
curl -s http://localhost:8000/api/v1/clusters/latest | jq '.clusters[] | {label, note_count}'
# {"label": "AWS Cloud Services", "note_count": 42}
# {"label": "Fitness Tracking", "note_count": 8}
# {"label": "Kubernetes Operations", "note_count": 15}
```

View duplicate pairs:

```bash
curl -s "http://localhost:8000/api/v1/similarity/duplicates/{job_id}?threshold=0.9" | jq
```

## 5. Generate a MOC from a cluster

Pick a cluster ID from the clusters response:

```bash
curl -X POST http://localhost:8000/api/v1/clusters/{cluster_id}/moc \
  -H 'Content-Type: application/json' \
  -d '{"target_folder": "30 Maps/"}' | jq
```

Preview the draft in the response `preview` field. Approve or reject:

```bash
# Approve -- writes the MOC to the vault
curl -X POST http://localhost:8000/api/v1/patches/{patch_id}/approve

# Reject -- discards the draft
curl -X POST http://localhost:8000/api/v1/patches/{patch_id}/reject
```

## 6. Incremental re-embedding

After editing notes, re-run embedding. Only changed notes are processed:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"job_type": "embed_notes", "target_path": "/"}' | jq
```

Check that only changed notes were re-embedded:

```bash
curl -s http://localhost:8000/api/v1/jobs/{job_id} | jq '.result'
# {"notes_embedded": 3, "notes_skipped": 632, "notes_total": 635}
```

## 7. Scoped embedding

Embed only a specific folder:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"job_type": "embed_notes", "target_path": "40 Projects/"}' | jq
```
