# Data Model: Batch Patch Operations & Undo/Rollback

## Entity Changes

### Modified: PatchOperation

Existing entity with the following changes:

**New enum value for PatchStatus**:
- `reverted` -- Added to the lifecycle. Set after a successful undo operation.

**Extended payload storage**:
- For `update_frontmatter_key` operations, the `payload` JSON column now also stores `previous_value` at apply time (the value of the key before the update). This enables reverse-apply during undo.
- For `append_body` and `prepend_body` operations, the `payload` already contains the `content` that was inserted, which is sufficient to locate and remove it during undo.

**State Transitions** (updated):

```
pending_approval --> approved --> applied --> reverted
                 \-> skipped
                 \-> failed
```

- New transition: `applied` --> `reverted` (via undo endpoint)
- `reverted` is a terminal state; a reverted patch cannot be re-applied or re-undone.

### Modified: Job

Existing entity with the following changes:

**New enum value for JobType**:
- `batch_patch` -- A job that applies the same operation(s) to multiple notes selected by folder or query.

### New: BatchPatchRequest (Pydantic schema only, not a DB entity)

Request body for batch patch operations.

| Field       | Type             | Required | Description                                                |
|-------------|------------------|----------|------------------------------------------------------------|
| folder_path | string           | no*      | Target folder path in the vault                            |
| query       | string           | no*      | Similarity search query text                               |
| threshold   | float            | no       | Similarity threshold (default 0.5), used with query        |
| limit       | int              | no       | Max notes to affect (query-based batches only)             |
| recursive   | bool             | no       | Include subfolders (default false), used with folder_path  |
| operations  | list[Operation]  | yes      | Operations to apply to each matched note                   |
| dry_run     | bool             | no       | Preview mode (default false)                               |

*Exactly one of `folder_path` or `query` must be provided.

### New: BatchPatchResult (Pydantic schema only)

Response for batch patch operations.

| Field          | Type                    | Description                                        |
|----------------|-------------------------|----------------------------------------------------|
| job_id         | string (UUID)           | Associated job ID                                  |
| target_count   | int                     | Total notes targeted                               |
| applied_count  | int                     | Notes where operations were applied                |
| skipped_count  | int                     | Notes skipped (no-op or already applied)           |
| pending_count  | int                     | Notes with high-risk ops pending approval          |
| failed_count   | int                     | Notes that failed to process                       |
| results        | list[NoteResult]        | Per-note result details                            |
| dry_run        | bool                    | Whether this was a preview                         |

### New: NoteResult (Pydantic schema only)

Per-note result within a batch response.

| Field       | Type           | Description                                              |
|-------------|----------------|----------------------------------------------------------|
| note_path   | string         | Path of the affected note                                |
| status      | string         | One of: applied, no_op, pending_approval, failed, would_apply, would_skip |
| patch_ids   | list[string]   | IDs of created PatchOperation records (empty for dry_run)|
| reason      | string or null | Additional context (error message, skip reason)          |

### New: UndoResponse (Pydantic schema only)

Response for single-patch undo.

| Field       | Type           | Description                                    |
|-------------|----------------|------------------------------------------------|
| status      | string         | "reverted" or error status                     |
| before_hash | string         | Content hash before undo (was after_hash)      |
| after_hash  | string         | Content hash after undo (matches original before_hash) |

### New: BatchUndoResponse (Pydantic schema only)

Response for batch undo (undo all patches from a job).

| Field           | Type              | Description                                    |
|-----------------|-------------------|------------------------------------------------|
| job_id          | string (UUID)     | Job whose patches were undone                  |
| reverted_count  | int               | Patches successfully reverted                  |
| conflict_count  | int               | Patches skipped due to note divergence         |
| error_count     | int               | Patches that failed to undo                    |
| results         | list[UndoDetail]  | Per-patch undo details                         |

### New: UndoDetail (Pydantic schema only)

Per-patch result within a batch undo response.

| Field            | Type           | Description                                          |
|------------------|----------------|------------------------------------------------------|
| patch_id         | string (UUID)  | ID of the PatchOperation                             |
| note_path        | string         | Path of the affected note                            |
| status           | string         | One of: reverted, conflict, error, skipped           |
| reason           | string or null | Conflict/error details                               |

## Relationships

- A `Job` with type `batch_patch` has many `PatchOperation` records (one per note per operation).
- Undo operations create new `OperationLog` entries referencing the original `PatchOperation`.
- Batch undo references a `Job` ID and iterates over its associated `PatchOperation` records.
