# Research: Note Similarity Engine

**Feature Branch**: `004-note-similarity-engine`
**Date**: 2026-03-13

## Research Area 1: Embedding Storage Strategy

**Decision**: Use pgvector extension with native VECTOR(1536) column type in PostgreSQL.

**Rationale**: pgvector provides SQL-native cosine similarity queries (`1 - (embedding <=> query_vector)`), compact binary storage, and clean SQLAlchemy integration via the `pgvector` Python package. At <10k rows, no ANN index is required -- sequential scan is fast enough. The only infrastructure change is swapping `postgres:16-alpine` for `pgvector/pgvector:pg16-alpine` in docker-compose.yml.

**Alternatives considered**:
- JSONB array: Works but forces all similarity computation into Python and uses 2-3x more storage. No SQL-native similarity operator.
- bytea/numpy serialization: Even harder to query in SQL. No tooling benefits.
- Separate vector store (Pinecone, Qdrant): Overkill for <10k vectors. Adds external dependency and violates local-first principle.

## Research Area 2: Embedding Model Selection

**Decision**: OpenAI text-embedding-3-small at 1536 dimensions.

**Rationale**: ~30% better than ada-002 on MTEB benchmarks. For note similarity on a personal vault (<5000 notes), the quality gap between small and large (3072 dims, 5x cost) is not meaningful. The `dimensions` API parameter allows future reduction (e.g., to 512) if storage becomes a concern.

**Alternatives considered**:
- text-embedding-3-large: ~10% better quality but 5x cost and double the storage. Not justified at this scale.
- Local models (sentence-transformers): Avoids sending content externally but adds heavy dependencies (PyTorch, ~2GB model download). Contradicts the lean Docker image approach.

## Research Area 3: Clustering Algorithm

**Decision**: HDBSCAN via scikit-learn (sklearn.cluster.HDBSCAN, available since scikit-learn 1.3).

**Rationale**: Does not require specifying cluster count (k). Automatically identifies noise points (unclustered notes) rather than forcing them into a poor-fit cluster. Primary tuning knob is `min_cluster_size` (default: 3). Available in scikit-learn with no additional package needed.

**Alternatives considered**:
- K-means: Requires specifying k. Forces every note into a cluster. Fragile when note count varies.
- Agglomerative clustering: Can work without k using a distance threshold, but threshold selection is fiddly. O(n^2) memory for large sets.

## Research Area 4: Similarity Computation Strategy

**Decision**: Hybrid approach -- pgvector for per-query nearest-neighbor search, numpy/scikit-learn for batch all-pairs duplicate detection.

**Rationale**: For single-note similarity search, pgvector's `ORDER BY embedding <=> query_vector LIMIT k` is efficient and runs in SQL. For batch duplicate detection (all-pairs cosine similarity), a numpy matmul over L2-normalized vectors completes in 1-3 seconds for 5k vectors and ~10-15 seconds for 10k. This is a background Celery task, so latency is acceptable. Full cross-join in SQL is slower than a vectorized Python operation for this pattern.

**Alternatives considered**:
- Pure SQL all-pairs: Awkward cross-join, slower than numpy matmul for batch operations.
- Pure Python for all queries: Works but misses pgvector's efficiency for interactive single-note search.

## New Dependencies Required

| Package | Purpose | Size |
|---------|---------|------|
| `pgvector` | SQLAlchemy Vector column type | ~50KB |
| `numpy` | Vector math, L2 normalization | ~25MB |
| `scikit-learn` | HDBSCAN clustering, cosine_similarity | ~30MB |

**Docker change**: `postgres:16-alpine` -> `pgvector/pgvector:pg16-alpine` in docker-compose.yml
