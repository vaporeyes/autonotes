# Implementation Plan: Batch Patch Operations & Undo/Rollback

**Branch**: `005-batch-patch-undo` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-batch-patch-undo/spec.md`

## Summary

Add batch patch operations that apply the same operation(s) across multiple notes selected by folder path or similarity query, plus an undo/rollback system that reverse-applies patches using the existing operation log's content hash verification. Batch operations follow the existing risk-tiered approval flow and run as background jobs for large batches. Undo works by constructing the inverse operation from the patch's stored payload and operation type.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Celery, SQLAlchemy (async), httpx, python-frontmatter
**Storage**: PostgreSQL 16 + pgvector (persistent), Redis 7 (Celery broker)
**Testing**: pytest
**Target Platform**: Linux server (Docker Compose)
**Project Type**: Web service (REST API + background worker)
**Performance Goals**: Batch 100+ notes in <60s, single undo <5s
**Constraints**: Surgical updates only (no full-file rewrites), all mutations logged
**Scale/Scope**: Single vault, ~700 notes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Data Integrity | PASS | Undo uses content hash verification before reverting. Batch operations continue on per-note failure, never leave partial state on a single note. Operation log captures every mutation. |
| II. Surgical Updates | PASS | Reuses existing patch engine (add_tag, remove_tag, etc.) which operates at key/line level. No full-file rewrites. |
| III. Local-First Privacy | PASS | No new external API calls. Similarity query reuses existing local embeddings. No note content leaves the network. |
| IV. Extensibility | PASS | Batch patches reuse existing operation types. New batch_patch job type registers alongside existing job types. Undo is a new endpoint on existing PatchOperation records. |
| V. Idempotency | PASS | Each note in a batch creates individual PatchOperation records with idempotency keys. Re-submitting the same batch is safe. Undo checks patch status before reverting (already-reverted is a no-op conflict). |

**Operational Constraints**:
- Backup granularity: Each note's before_hash is recorded per PatchOperation. For update_frontmatter_key, previous_value is stored in payload for undo.
- Conflict resolution: Content hash check before undo prevents overwriting concurrent edits.
- Vault boundaries: Single vault scope maintained.

**Post-design re-check**: All principles remain satisfied. The reverse-apply undo strategy (R1) specifically supports Principle I (recoverable state) without storing full snapshots.

## Project Structure

### Documentation (this feature)

```text
specs/005-batch-patch-undo/
  plan.md              # This file
  research.md          # Phase 0 output
  data-model.md        # Phase 1 output
  quickstart.md        # Phase 1 output
  contracts/
    api.md             # API contract
  checklists/
    requirements.md    # Spec quality checklist
  tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (changes to existing codebase)

```text
app/
  models/
    patch_operation.py   # MODIFY: Add 'reverted' to PatchStatus enum
    job.py               # MODIFY: Add 'batch_patch' to JobType enum
  schemas/
    batch_patch.py       # NEW: BatchPatchRequest, BatchPatchResult, NoteResult schemas
    undo.py              # NEW: UndoResponse, BatchUndoResponse, UndoDetail schemas
  services/
    patch_engine.py      # MODIFY: Add reverse_apply_patch() function
    batch_patch_service.py  # NEW: Batch note selection, batch apply logic, dry-run
    undo_service.py      # NEW: Single undo, batch undo, hash verification
  api/routes/
    batch_patches.py     # NEW: POST /batch-patches endpoint
    patches.py           # MODIFY: Add POST /patches/{id}/undo endpoint
    jobs.py              # MODIFY: Add POST /jobs/{id}/undo endpoint, batch_patch dispatch
  tasks/
    batch_patch_job.py   # NEW: Celery task for async batch operations
  celery_app.py          # MODIFY: Register batch_patch_job task
  main.py                # MODIFY: Register batch_patches router
  db/migrations/versions/
    xxxx_add_batch_patch_undo.py  # NEW: Add reverted status, batch_patch job type
```

**Structure Decision**: Extends existing codebase structure. New files follow the established pattern (service per domain, route per resource group, Celery task per job type). No new top-level directories needed.
