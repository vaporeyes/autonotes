# Research: Auto-Triage for Vault Notes

**Date**: 2026-03-12
**Feature Branch**: `003-auto-triage`

## 1. Convention Inheritance Resolution Strategy

**Decision**: Walk the folder path from root to leaf, merging conventions
at each level. Child entries override parent entries for the same key
(frontmatter field name, tag value, or backlink target folder).

**Rationale**: FR-002 requires additive inheritance with per-field
override. The simplest approach is to query all conventions whose
folder_path is a prefix of the note's path, ordered by path depth
(shortest first), then merge them left-to-right. For a note at
`projects/active/sprint-1.md`, the system queries conventions for `/`,
`projects/`, and `projects/active/` (if they exist), merging each into
the accumulated rule set. This is a single DB query with a prefix match,
followed by in-memory merge.

**Alternatives considered**:
- Recursive parent FK traversal: Each convention points to its parent.
  Requires multiple queries or recursive CTE. Unnecessary complexity
  when a simple prefix query + sort achieves the same result.
- Precomputed merged conventions (materialized): Cache the merged result
  per folder. Adds cache invalidation complexity for minimal gain given
  vault sizes of hundreds to low thousands of notes.

## 2. Rejection Tracking to Prevent Re-suggestion

**Decision**: Store a `rejected_hash` on each TriageIssue record when the
user rejects the corresponding patch. The hash is computed from
(note_path, issue_type, suggested_fix_payload). On subsequent scans,
before creating a new issue, check if a matching rejected_hash exists
where the note's modification timestamp is older than the rejection
timestamp.

**Rationale**: FR-009 requires that rejected suggestions are not
re-surfaced until the note is modified. Comparing note modification
time against rejection time is the simplest guard. The rejected_hash
allows efficient lookup without parsing the full suggestion payload.
When the note is modified (its timestamp advances past the rejection
time), the guard expires naturally.

**Alternatives considered**:
- Separate rejection table: Adds a new entity for a single boolean-like
  check. Overkill. A column on TriageIssue is sufficient.
- Redis-based rejection cache: Ephemeral storage risks losing rejection
  state on Redis restart. DB is the right persistence layer.

## 3. Triage Scan Concurrency and Note Ordering

**Decision**: Process notes sequentially within a single Celery task.
For each note: read content, compute hash, check conventions, detect
issues, apply low-risk fixes (re-verifying hash before write), create
pending patches for high-risk issues.

**Rationale**: The existing vault_scan and vault_health_scan tasks use
the same sequential pattern. At 500 notes with ~100ms per note (read +
parse + optional write), the scan completes in ~50 seconds, within the
60-second target. Parallelizing adds complexity (concurrent writes to
the same note, partial failure recovery) without meaningful benefit at
this scale.

**Alternatives considered**:
- Parallel note processing with asyncio.gather: Risks concurrent patches
  on the same note if two notes trigger cross-referencing fixes.
  Constitution requires conflict detection, which is simpler with
  sequential processing.
- Batch all patches and apply at end: Requires holding all note content
  in memory and re-reading for hash verification. Sequential
  read-check-write is simpler and matches existing patterns.

## 4. Reusing Existing Patch System for Auto-Apply

**Decision**: For each low-risk issue, the triage service calls
`patch_engine.apply_patch()` directly within the scan loop, then writes
back via `obsidian_client.put_note()`. Each applied patch creates a
PatchOperation record linked to the triage scan job, reusing the
existing logging through `log_service.create_log()`.

**Rationale**: The patch engine already handles idempotency (no-op if
tag exists, no-op if frontmatter key matches). The patches route
(`patches.py`) demonstrates the full pattern: read note, compute hash,
apply patch, write back, log. The triage service follows the same
pattern internally without going through the HTTP endpoint.

**Alternatives considered**:
- Call the /patches HTTP endpoint from the Celery task: Adds HTTP
  overhead and circular dependency (worker calling its own API).
  Direct service-layer calls are simpler and faster.
- Create all patches as pending and auto-approve low-risk ones: Adds
  unnecessary DB round-trips. The existing patches route already
  auto-applies low-risk ops inline; the triage service does the same.
