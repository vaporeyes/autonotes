# API Contract: Note Similarity Engine

**Feature Branch**: `004-note-similarity-engine`
**Base Path**: `/api/v1`

## New Endpoints

### Similarity Search

#### POST /similarity/search

Find notes similar to a given note or free-text query.

**Request Body**:
```json
{
  "note_path": "20 Permanent/Architecture/Cloud/microservices-patterns.md",
  "query": null,
  "threshold": 0.5,
  "limit": 20
}
```

- `note_path` (string, optional): Path to the source note. Mutually exclusive with `query`.
- `query` (string, optional): Free-text query to embed and search against. Mutually exclusive with `note_path`.
- `threshold` (float, optional, default: 0.5): Minimum similarity score (0.0-1.0).
- `limit` (integer, optional, default: 20, max: 100): Maximum results to return.

Exactly one of `note_path` or `query` must be provided.

**Response** (200):
```json
{
  "source": "20 Permanent/Architecture/Cloud/microservices-patterns.md",
  "results": [
    {
      "note_path": "20 Permanent/Architecture/Cloud/service-mesh.md",
      "similarity": 0.87,
      "title": "Service Mesh Patterns",
      "tags": ["architecture", "cloud"]
    }
  ],
  "total": 5,
  "threshold": 0.5,
  "embedded_on_the_fly": false
}
```

- `source` (string): The note path or "[free-text query]" indicator.
- `results` (array): Ranked by descending similarity.
- `embedded_on_the_fly` (boolean): True if the source note was embedded as part of this request.

**Errors**:
- 400: Neither `note_path` nor `query` provided, or both provided
- 404: `note_path` does not exist in the vault
- 422: No embeddings exist (must run embedding job first)

---

### Duplicate Detection

#### GET /similarity/duplicates/{job_id}

Get duplicate pairs detected by a clustering/duplicate detection job.

**Path Parameters**:
- `job_id` (UUID): The job that ran duplicate detection.

**Query Parameters**:
- `threshold` (float, optional, default: 0.9): Minimum similarity to include.
- `limit` (integer, optional, default: 50, max: 200): Maximum pairs to return.

**Response** (200):
```json
{
  "job_id": "abc-123",
  "threshold": 0.9,
  "pairs": [
    {
      "note_path_a": "20 Permanent/Cloud/AWS/EC2.md",
      "note_path_b": "100 Archive/devlog/devlog.ec2.md",
      "similarity": 0.94,
      "excerpt_a": "EC2 is Amazon's virtual machine service...",
      "excerpt_b": "Amazon EC2 provides scalable compute..."
    }
  ],
  "total": 3
}
```

**Errors**:
- 404: Job not found or not a clustering job

---

### Clusters

#### GET /clusters/latest

Get clusters from the most recent clustering job.

**Query Parameters**:
- `min_size` (integer, optional, default: 2): Minimum notes per cluster to include.

**Response** (200):
```json
{
  "job_id": "def-456",
  "created_at": "2026-03-13T10:00:00Z",
  "clusters": [
    {
      "id": "cluster-uuid-1",
      "label": "AWS Cloud Services",
      "note_count": 42,
      "notes": [
        {
          "note_path": "20 Permanent/Cloud/AWS/EC2.md",
          "similarity_to_centroid": 0.91
        }
      ]
    }
  ],
  "unclustered_count": 15,
  "total_clusters": 8
}
```

**Errors**:
- 422: No clustering job has been run yet

---

#### GET /clusters/{cluster_id}

Get details of a specific cluster.

**Response** (200):
```json
{
  "id": "cluster-uuid-1",
  "job_id": "def-456",
  "label": "AWS Cloud Services",
  "note_count": 42,
  "notes": [
    {
      "note_path": "20 Permanent/Cloud/AWS/EC2.md",
      "similarity_to_centroid": 0.91,
      "title": "EC2",
      "tags": ["aws"]
    }
  ],
  "created_at": "2026-03-13T10:00:00Z"
}
```

**Errors**:
- 404: Cluster not found

---

### MOC Generation

#### POST /clusters/{cluster_id}/moc

Generate a MOC (Map of Content) draft from a cluster.

**Request Body**:
```json
{
  "target_folder": "30 Maps/",
  "title": null
}
```

- `target_folder` (string, optional, default: "30 Maps/"): Where to write the MOC.
- `title` (string, optional): Override the auto-generated title.

**Response** (201):
```json
{
  "patch_id": "patch-uuid-1",
  "target_path": "30 Maps/AWS Cloud Services.md",
  "preview": "# AWS Cloud Services\n\nA collection of notes about...\n\n## Notes\n\n- [[20 Permanent/Cloud/AWS/EC2.md|EC2]]\n...",
  "note_count": 42,
  "status": "pending_approval"
}
```

The returned `patch_id` can be approved or rejected via the existing patch endpoints:
- `POST /patches/{patch_id}/approve` -- writes the MOC to the vault
- `POST /patches/{patch_id}/reject` -- discards the draft

**Errors**:
- 404: Cluster not found
- 400: Cluster has fewer than 2 notes
- 409: A MOC with a similar name already exists at the target path

---

### Embedding Management

#### GET /embeddings/status

Get the current state of the embedding index.

**Response** (200):
```json
{
  "total_embedded": 485,
  "total_vault_notes": 647,
  "stale_count": 12,
  "last_job_id": "ghi-789",
  "last_embedded_at": "2026-03-13T05:00:00Z",
  "model": "text-embedding-3-small",
  "coverage_percent": 74.9
}
```

- `stale_count`: Notes whose content has changed since last embedding.
- `coverage_percent`: Percentage of vault notes that have current embeddings.

---

## Modified Endpoints

### POST /jobs (existing)

Add new job types:

```json
{
  "job_type": "embed_notes",
  "target_path": "/",
  "params": {
    "force": false
  }
}
```

- `job_type: "embed_notes"`: Run vault-wide embedding. `target_path` scopes the folders. `force: true` re-embeds all notes regardless of content hash.

```json
{
  "job_type": "cluster_notes",
  "params": {
    "min_cluster_size": 3,
    "duplicate_threshold": 0.9
  }
}
```

- `job_type: "cluster_notes"`: Run clustering and duplicate detection. `min_cluster_size` controls HDBSCAN sensitivity. `duplicate_threshold` controls the similarity cutoff for duplicate pairs.

## OpenAPI Tags

- **Similarity**: Similarity search and duplicate detection
- **Clusters**: Topic clustering and MOC generation
- **Embeddings**: Embedding index status

## Configuration Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model name |
| `EMBEDDING_DIMENSIONS` | `1536` | Vector dimensions |
| `EMBEDDING_EXCLUDE_PATTERNS` | `90 Atlas/Templates/,Attachments/,images/` | Comma-separated folder prefixes to skip |
| `EMBEDDING_BATCH_SIZE` | `50` | Notes per OpenAI API call batch |
| `SIMILARITY_DEFAULT_THRESHOLD` | `0.5` | Default minimum similarity for search |
| `DUPLICATE_DEFAULT_THRESHOLD` | `0.9` | Default threshold for duplicate detection |
| `CLUSTER_MIN_SIZE` | `3` | Default HDBSCAN min_cluster_size |
| `MOC_TARGET_FOLDER` | `30 Maps/` | Default folder for generated MOCs |
| `EMBEDDING_SCAN_CRON` | `0 4 * * *` | Cron schedule for periodic embedding job |
| `CLUSTER_SCAN_CRON` | `0 4 30 * *` | Cron schedule for periodic clustering (monthly) |
