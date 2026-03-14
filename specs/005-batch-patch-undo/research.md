# Research: Batch Patch Operations & Undo/Rollback

## R1: Reverse-Apply Strategy for Undo Operations

**Decision**: Use deterministic inverse operations to reverse patches rather than storing full content snapshots.

**Rationale**: Each existing operation type has a clear inverse:
- `add_tag` undone by `remove_tag`
- `remove_tag` undone by `add_tag`
- `add_backlink` undone by `remove_backlink`
- `remove_backlink` undone by `add_backlink`
- `update_frontmatter_key` undone by `update_frontmatter_key` with the previous value (stored in payload)
- `append_body` undone by removing the appended content (stored in payload)
- `prepend_body` undone by removing the prepended content (stored in payload)
- `create_moc` undone by deleting the created file (target_path known)

The content hash verification (`after_hash` check before undo) ensures the note hasn't been modified since the patch, making reverse-apply safe. The patch's `payload` already stores enough information to construct the inverse operation.

**Alternatives considered**:
- Full content snapshots: Would require storing entire note contents in the database, significantly increasing storage requirements. Rejected because the payload + hash approach is sufficient and lightweight.
- Git-style diffs: Would add complexity for marginal benefit since our operations are structured, not arbitrary text edits.

## R2: Batch Job Threshold and Execution Model

**Decision**: Batch operations with more than 10 target notes run as background Celery jobs. 10 or fewer run synchronously in the API request.

**Rationale**: The existing job system (Celery + Redis) already handles background tasks with progress tracking. Small batches (<=10 notes) complete fast enough for synchronous HTTP responses. This matches the existing pattern where single-note patches run synchronously.

**Alternatives considered**:
- Always async: Would add unnecessary complexity for small batches (2-3 notes).
- Always sync: Would cause HTTP timeouts on large batches (100+ notes).
- User-chosen: Adds API complexity without clear benefit; the threshold handles both cases.

## R3: Batch Scope Selection Mechanisms

**Decision**: Two scope mechanisms -- folder path (with recursive flag) and similarity query (with threshold + limit).

**Rationale**: Folder-based selection is the most intuitive and common use case. Similarity-based selection leverages the existing embedding engine (spec 004) for intelligent bulk operations. Both use existing infrastructure (ObsidianClient.list_folder and similarity_service.search_similar).

**Alternatives considered**:
- Tag-based selection (e.g., "all notes with tag X"): Useful but can be achieved by combining similarity search with tag-specific queries. Deferred to avoid scope creep.
- Glob patterns: More flexible than folder path but adds parsing complexity. Folder + recursive covers the primary use case.

## R4: Storing Undo Metadata

**Decision**: Store the original payload and operation type in the existing PatchOperation record. For `update_frontmatter_key`, the before-value must be captured at apply time and stored in the payload.

**Rationale**: The PatchOperation already stores `operation_type`, `payload`, `before_hash`, and `after_hash`. For most operations (add_tag, add_backlink), the payload contains enough to construct the inverse. For `update_frontmatter_key`, we need to also store the previous value of the key so we can restore it. This means extending the payload at apply time to include `previous_value`.

**Alternatives considered**:
- Separate undo metadata table: Adds schema complexity for data that naturally belongs with the patch record.
- Storing full before-content: Excessive for structured operations where the inverse is deterministic.
