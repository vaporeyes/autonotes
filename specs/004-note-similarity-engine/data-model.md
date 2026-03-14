# Data Model: Note Similarity Engine

**Feature Branch**: `004-note-similarity-engine`
**Date**: 2026-03-13

## Entities

### NoteEmbedding

Stores a vector embedding for a single vault note. One row per note (latest version). Stale embeddings are detected via content hash comparison.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| note_path | VARCHAR(1024) | NOT NULL, UNIQUE | Vault-relative path to the note |
| content_hash | VARCHAR(64) | NOT NULL | SHA-256 hash of the note body (excluding frontmatter) |
| embedding | VECTOR(1536) | NOT NULL | OpenAI text-embedding-3-small vector |
| token_count | INTEGER | NOT NULL | Tokens consumed for this embedding |
| model | VARCHAR(64) | NOT NULL, default 'text-embedding-3-small' | Embedding model used |
| embedded_at | TIMESTAMPTZ | NOT NULL | When the embedding was last generated |
| created_at | TIMESTAMPTZ | NOT NULL | Row creation time |

**Indexes**:
- `ix_note_embedding_path` on `note_path` (unique)
- `ix_note_embedding_hash` on `content_hash`

**Lifecycle**:
- Created when a note is first embedded (via batch job or on-the-fly)
- Updated in-place when a note is re-embedded after content change (content_hash + embedding + token_count + embedded_at updated)
- Marked stale or deleted when the source note no longer exists in the vault

---

### NoteCluster

Represents a topic cluster produced by a clustering job. Each clustering run replaces all previous clusters.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| job_id | UUID | FK -> jobs.id, NOT NULL | The clustering job that produced this cluster |
| label | VARCHAR(256) | NOT NULL | Human-readable cluster label |
| note_count | INTEGER | NOT NULL | Number of notes in this cluster |
| created_at | TIMESTAMPTZ | NOT NULL | When the cluster was created |

**Indexes**:
- `ix_note_cluster_job_id` on `job_id`

---

### ClusterMember

Join table linking notes to clusters. A note belongs to at most one cluster per clustering run (or none if unclustered).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| cluster_id | UUID | FK -> note_clusters.id, NOT NULL, CASCADE | Parent cluster |
| note_path | VARCHAR(1024) | NOT NULL | Vault-relative path to the note |
| similarity_to_centroid | FLOAT | NOT NULL | How similar this note is to the cluster center |

**Indexes**:
- `ix_cluster_member_cluster_id` on `cluster_id`
- `ix_cluster_member_note_path` on `note_path`

---

### DuplicatePair

Stores detected near-duplicate note pairs from a duplicate detection scan. Persisted per job run.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| job_id | UUID | FK -> jobs.id, NOT NULL | The duplicate detection job |
| note_path_a | VARCHAR(1024) | NOT NULL | First note in the pair |
| note_path_b | VARCHAR(1024) | NOT NULL | Second note in the pair |
| similarity_score | FLOAT | NOT NULL | Cosine similarity between the two notes |
| created_at | TIMESTAMPTZ | NOT NULL | When the pair was detected |

**Indexes**:
- `ix_duplicate_pair_job_id` on `job_id`
- Unique constraint on `(job_id, note_path_a, note_path_b)` to prevent duplicate entries per scan

---

### MOCDraft (virtual / reuses PatchOperation)

MOC drafts reuse the existing `PatchOperation` model with a new operation type. No new table needed.

- `op_type`: `create_moc` (new enum value)
- `target_path`: The path where the MOC will be written (e.g., `30 Maps/AWS Architecture.md`)
- `payload`: The generated Markdown content
- `status`: `pending_approval` -> `approved` / `rejected`
- `metadata`: JSON with `cluster_id` reference

This reuses the existing approval workflow (POST /patches/{id}/approve, POST /patches/{id}/reject).

## Relationships

```
Job 1---* NoteCluster (one clustering job produces many clusters)
NoteCluster 1---* ClusterMember (one cluster has many member notes)
Job 1---* DuplicatePair (one duplicate scan produces many pairs)
PatchOperation (op_type=create_moc) references cluster via metadata
```

## Enum Additions

### JobType (existing enum, add new values)

- `embed_notes` -- vault-wide embedding job
- `cluster_notes` -- clustering job (also runs duplicate detection)

### OpType (existing enum, add new value)

- `create_moc` -- create a new MOC note in the vault

## Migration Notes

- New tables: `note_embeddings`, `note_clusters`, `cluster_members`, `duplicate_pairs`
- Requires pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;` in migration
- Add `embed_notes` and `cluster_notes` to `job_type_enum`
- Add `create_moc` to `op_type_enum`
- Migration revision chains from latest existing migration
