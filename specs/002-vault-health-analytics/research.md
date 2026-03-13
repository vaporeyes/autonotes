# Research: Vault Health Analytics

**Date**: 2026-03-12
**Feature Branch**: `002-vault-health-analytics`

## 1. Graph Connectivity Algorithm for Cluster Detection

**Decision**: Union-Find (disjoint set) with path compression and union
by rank.

**Rationale**: FR-003 requires detecting disconnected clusters in the
backlink graph (treating links as bidirectional). Union-Find is O(n *
alpha(n)) -- effectively O(n) -- for n edges, uses O(n) memory, and
produces cluster counts and sizes directly. For 5000 notes this
completes in milliseconds. No external dependency needed; implement
inline (~30 lines).

**Alternatives considered**:
- BFS/DFS connected components: Also O(V+E) but requires building an
  explicit adjacency list first. Union-Find avoids the adjacency list
  by processing edges as they're discovered during note parsing.
- NetworkX library: Full graph library. Overkill for a single
  connected-components query. Adds ~15MB dependency for one function.

## 2. Composite Score Normalization

**Decision**: Each sub-metric normalized to 0-100 using domain-specific
formulas before applying the weighted formula from clarifications
(backlink density 30%, orphan ratio 30%, connectivity 25%, tags 15%).

**Rationale**: Raw metric values have different scales (orphan count is
0-N, density is a float, cluster count is 1-N). Normalization makes the
weighted sum meaningful. Specific formulas:

- **Orphan ratio score**: `100 * (1 - orphan_count / total_notes)`.
  Zero orphans = 100. All orphans = 0.
- **Backlink density score**: `min(100, density * 20)`. Density of 5.0+
  links/note = perfect 100. Zero links = 0. Linear scale.
- **Cluster connectivity score**: `100 * (1 / cluster_count)`. One
  cluster (fully connected) = 100. Two clusters = 50. Diminishes with
  fragmentation.
- **Tag distribution score**: `min(100, unique_tags / total_notes * 200)`.
  Healthy vaults have ~0.5+ unique tags per note. Rewards tag diversity
  up to the cap.

**Alternatives considered**:
- Percentile-based normalization (against historical data): Requires
  existing history, breaks on first scan. Rejected.
- Z-score normalization: Requires population statistics. Not applicable
  for single-vault use.

## 3. Snapshot Retention and Purge Strategy

**Decision**: Reuse the existing Celery beat pattern from log_purge.py.
Add a `health_snapshot_purge` beat entry that runs daily, deleting
snapshots older than 365 days.

**Rationale**: The log_purge task already demonstrates the pattern
(scheduled Celery beat, date comparison, bulk delete). Consistent
approach. No new infrastructure.

**Alternatives considered**:
- PostgreSQL partitioning by month: Useful at scale but premature for
  single-user vaults with at most ~365 rows/year per scope.
- TTL via database triggers: PostgreSQL lacks native TTL. Would require
  pg_cron extension, adding operational complexity.

## 4. Reusing the Existing Note Parser

**Decision**: Reuse `note_parser.py` to extract tags and backlinks from
each note. The health service calls `obsidian_client.list_folder()` to
enumerate notes, then `obsidian_client.get_note_raw()` for each, then
`note_parser.parse_note()` to extract structured data.

**Rationale**: The parser already extracts exactly the fields needed
(tags, backlinks). No new parsing logic required. The scan iterates
notes and aggregates the parsed results into metrics.

**Alternatives considered**:
- Direct Obsidian API queries for tags/links: The Obsidian REST API
  does not expose a bulk tag/link query endpoint. Must read individual
  files.
- Caching parsed results in PostgreSQL: Premature optimization. At 5000
  notes with ~2KB each, the full scan is ~10MB of I/O -- well within
  the 60-second target.
