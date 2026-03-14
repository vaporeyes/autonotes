# Feature Specification: Batch Patch Operations & Undo/Rollback

**Feature Branch**: `005-batch-patch-undo`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Add batch patch operations (apply the same operation across multiple notes by folder or query) and an undo/rollback system that uses existing operation logs to revert patches to their previous content hash state."

## Clarifications

### Session 2026-03-14

- Q: When undoing a patch from a multi-operation request, should undo revert the single operation or the entire group? → A: Individual operation undo (revert one PatchOperation at a time).
- Q: Should there be a time limit on how far back a patch can be undone? → A: No time limit. Undo is allowed as long as the patch record exists and the note hasn't diverged.

## User Scenarios & Testing

### User Story 1 - Batch Patch by Folder (Priority: P1)

A vault maintainer wants to apply the same tag to all notes in a folder (e.g., add `#archived` to every note in `00 Fleeting/`). Today, they must submit individual patch requests per note. With batch patching, they submit one request specifying a folder path and operation, and the system applies it across all matching notes.

**Why this priority**: Batch operations are the most common power-user need and deliver immediate productivity gains. Every other batch feature builds on this foundation.

**Independent Test**: Submit a batch patch request targeting a folder with a known set of notes, verify each note receives the operation, and confirm the response reports per-note results.

**Acceptance Scenarios**:

1. **Given** a folder `00 Fleeting/` with 5 markdown notes, **When** the user submits a batch patch to add tag `#review` targeting that folder, **Then** all 5 notes receive the `#review` tag and the response lists per-note results with status.
2. **Given** a batch patch targeting a folder, **When** some notes already have the tag, **Then** those notes are reported as no-op and only notes needing the change are modified.
3. **Given** a batch patch with a high-risk operation (e.g., add_backlink), **When** the batch is submitted, **Then** each note's operation follows the existing risk-tiered approval flow (low-risk auto-applies, high-risk queues for approval).
4. **Given** a folder containing subfolders, **When** the user submits a batch patch with `recursive: true`, **Then** all notes in the folder and its subfolders are included.

---

### User Story 2 - Batch Patch by Similarity Query (Priority: P2)

A vault maintainer wants to apply an operation to notes that match a similarity search query (e.g., add tag `#kubernetes` to all notes similar to "Kubernetes deployment strategies"). This leverages the existing embedding-based similarity search to select target notes dynamically.

**Why this priority**: Builds on the similarity engine from spec 004 and the batch infrastructure from US1 to enable intelligent, query-driven bulk edits.

**Independent Test**: Run a similarity query, verify matching notes are returned, submit a batch patch using that query, and confirm the operation is applied to the matched notes.

**Acceptance Scenarios**:

1. **Given** embedded vault notes, **When** the user submits a batch patch with a similarity query `"kubernetes deployments"` and threshold `0.6`, **Then** all notes matching the query above the threshold receive the specified operation.
2. **Given** a similarity-based batch patch, **When** the result set is large (50+ notes), **Then** the operation runs as a background job with progress tracking rather than synchronously.
3. **Given** a batch patch with a query, **When** an optional `limit` is specified, **Then** only the top N most similar notes are affected.

---

### User Story 3 - Undo a Single Patch (Priority: P3)

A vault maintainer realizes a previously applied patch was a mistake (e.g., wrong tag added, bad backlink). They want to undo that specific patch by reverting the note to its state before the patch was applied. The system uses the operation log's before/after content hashes to verify the note hasn't been modified since, then restores the previous content.

**Why this priority**: Single-patch undo is the simplest rollback case and provides immediate safety for accidental changes. It lays the groundwork for batch undo.

**Independent Test**: Apply a patch to a note, then undo it via the undo endpoint. Verify the note content matches its pre-patch state and the undo is logged in the audit trail.

**Acceptance Scenarios**:

1. **Given** a patch operation with status `applied` and a recorded `before_hash`, **When** the user requests undo for that patch, **Then** the system verifies the note's current content matches the patch's `after_hash`, reverse-applies the operation, and restores the note.
2. **Given** a patch that was applied, **When** the note has been modified since (current hash does not match `after_hash`), **Then** the undo is rejected with a conflict error explaining the note has diverged.
3. **Given** a patch with status `pending_approval` or `skipped`, **When** undo is requested, **Then** the system returns an error stating only applied patches can be undone.
4. **Given** a successful undo, **When** the undo completes, **Then** an operation log entry is created recording the reversal with before/after hashes, and the patch status is updated to `reverted`.

---

### User Story 4 - Undo a Batch Operation (Priority: P4)

A vault maintainer applied a batch patch to 20 notes and wants to undo the entire batch. They submit an undo request for the batch job, and the system reverts all successfully applied patches from that job, skipping any that have diverged since application.

**Why this priority**: Extends single undo (US3) to batch scope, providing safety for the batch operations introduced in US1/US2.

**Independent Test**: Apply a batch patch to multiple notes, then undo the entire batch by job ID. Verify all notes are reverted and the response reports per-note undo results.

**Acceptance Scenarios**:

1. **Given** a completed batch job with 10 applied patches, **When** the user requests batch undo by job ID, **Then** all 10 patches are reverted and the response lists per-note undo results.
2. **Given** a batch undo where 3 of 10 notes have been modified since the batch was applied, **Then** those 3 are skipped with conflict status and the remaining 7 are successfully reverted.
3. **Given** a batch undo request, **When** the operation completes, **Then** an audit trail entry is created for each individual undo operation.

---

### User Story 5 - Preview Batch Operations (Priority: P5)

Before committing to a batch operation, a vault maintainer wants to preview which notes would be affected and what changes would be made. They submit a batch request in dry-run mode and receive a summary without any modifications being applied.

**Why this priority**: Safety feature that reduces mistakes, but not required for core functionality.

**Independent Test**: Submit a batch patch with `dry_run: true`, verify the response lists affected notes and planned changes, and confirm no notes were modified.

**Acceptance Scenarios**:

1. **Given** a batch patch request with `dry_run: true`, **When** submitted, **Then** the response lists all notes that would be affected, the operation that would be applied, and whether each would be a change or no-op, without modifying any notes.
2. **Given** a dry-run batch targeting a folder with 50 notes, **When** the response is returned, **Then** it includes a summary count (e.g., `would_apply: 42, would_skip: 8`).

---

### Edge Cases

- What happens when a batch targets an empty folder? The system returns a success response with zero results and no modifications.
- What happens when a batch folder path doesn't exist? The system returns a 404 error with a descriptive message.
- What happens when undo is attempted on a patch whose note has been deleted from the vault? The undo is rejected with an error explaining the note no longer exists.
- What happens when multiple undo requests are submitted for the same patch concurrently? The first succeeds and the second fails with a conflict error (patch status is no longer `applied`).
- What happens when a batch operation encounters an Obsidian API error mid-batch? The system continues processing remaining notes, marks the failed note as `failed` in the results, and reports a partial success.

## Requirements

### Functional Requirements

**Batch Operations**

- **FR-001**: System MUST accept a batch patch request specifying a folder path and one or more operations to apply to all markdown notes in that folder.
- **FR-002**: System MUST support a `recursive` flag to include notes in subfolders when targeting a folder.
- **FR-003**: System MUST accept a batch patch request specifying a similarity query (free-text string and threshold) to select target notes dynamically.
- **FR-004**: Each note in a batch MUST follow the existing risk-tiered approval flow (low-risk auto-applies, high-risk queues for approval).
- **FR-005**: System MUST run batch operations exceeding 10 notes as background jobs with progress tracking.
- **FR-006**: System MUST report per-note results (applied, no-op, pending_approval, failed) in the batch response.
- **FR-007**: System MUST support a `dry_run` flag that returns a preview of affected notes without applying changes.
- **FR-008**: System MUST support a `limit` parameter for query-based batches to cap the number of affected notes.

**Undo/Rollback**

- **FR-009**: System MUST provide an undo endpoint that reverts a single applied patch operation to its pre-patch state. Undo targets individual PatchOperation records, not grouped requests.
- **FR-010**: System MUST verify the note's current content hash matches the patch's `after_hash` before allowing undo, rejecting with a conflict if the note has diverged.
- **FR-011**: System MUST reconstruct the pre-patch note content by reverse-applying the original patch operation (e.g., undo add_tag by remove_tag), rather than storing full content snapshots.
- **FR-012**: System MUST provide a batch undo endpoint that reverts all applied patches from a given job ID.
- **FR-013**: Batch undo MUST skip patches whose notes have diverged and report per-note undo results (reverted, conflict, error).
- **FR-014**: System MUST add a `reverted` status to the patch lifecycle and update the patch status after successful undo.
- **FR-015**: Every undo operation MUST create an audit trail entry in the operation log with before/after content hashes.

### Key Entities

- **BatchPatchRequest**: Represents a request to apply operations across multiple notes, selected by folder path or similarity query. Includes operations list, scope parameters (folder, query, threshold, limit), dry_run flag, and recursive flag.
- **BatchPatchResult**: Aggregated response containing per-note results, summary counts, and the associated job ID.
- **UndoResult**: Response containing the revert status per note, before/after hashes, and any conflict details.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can apply the same operation to all notes in a folder with a single request instead of one request per note.
- **SC-002**: Batch operations on 100+ notes complete within 60 seconds.
- **SC-003**: Users can undo any previously applied patch within 5 seconds, provided the note has not been externally modified.
- **SC-004**: Batch undo of a 50-note batch completes within 30 seconds, reverting all unmodified notes and reporting conflicts for modified ones.
- **SC-005**: Dry-run preview of a batch operation returns results within 10 seconds for folders with up to 200 notes.
- **SC-006**: 100% of undo operations are reflected in the audit trail with accurate before/after content hashes.

## Assumptions

- The existing Obsidian Local REST API folder listing endpoint returns all files in a folder and supports recursive traversal via the existing `list_folder` method.
- Undo relies on reverse-applying patch operations (e.g., undo add_tag by remove_tag) rather than storing full note content snapshots. This is possible because each operation type has a deterministic inverse.
- The similarity search engine (spec 004) is deployed and functional before query-based batch operations are available.
- Batch operations share the same idempotency guarantees as single-patch operations (duplicate batch requests with the same operations and targets are safe to retry).
