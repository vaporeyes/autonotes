<!--
Sync Impact Report
==================
Version change: 0.0.0 (template) -> 1.0.0
Added principles:
  - I. Data Integrity
  - II. Surgical Updates
  - III. Local-First Privacy
  - IV. Extensibility
  - V. Idempotency
Added sections:
  - Operational Constraints
  - Development Workflow
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md: no updates needed (Constitution Check is generic)
  - .specify/templates/spec-template.md: no updates needed (requirements are generic)
  - .specify/templates/tasks-template.md: no updates needed (phase structure is generic)
Follow-up TODOs: none
-->

# Autonotes Constitution

## Core Principles

### I. Data Integrity

- All write operations MUST create a recoverable state before modifying
  note content. This means either a backup copy or a reversible patch.
- Full-file overwrites of existing notes are prohibited. If a tool or
  operation cannot produce a targeted patch, it MUST snapshot the
  original content before writing.
- Every mutation MUST be attributable: the operation name, timestamp,
  and affected file path MUST be logged or embedded in metadata.
- On failure mid-write, the system MUST leave the note in its
  pre-operation state, not a partial state.

**Rationale**: User notes are irreplaceable creative work. A single
corrupted overwrite can destroy hours of thought. Recovery MUST always
be possible.

### II. Surgical Updates

- Prefer targeted content patches (append, prepend, search-and-replace,
  or JSON Patch style operations) over full-file rewrites.
- When modifying structured frontmatter, use key-level merge semantics:
  only the changed keys are touched; unrelated keys MUST remain intact.
- When modifying body content, use the narrowest operation available
  (e.g., `obsidian_patch_content` or line-range replacement) rather
  than rewriting the entire file.
- Diffs MUST be human-readable. Any automated change MUST be
  expressible as a concise before/after delta.

**Rationale**: Surgical updates reduce merge conflicts, minimize data
loss risk, and make automated changes auditable.

### III. Local-First Privacy

- All LLM processing MUST operate on data that stays within the user's
  local environment. No note content may be sent to remote services
  unless the user has explicitly opted in for that specific operation.
- Tool definitions MUST NOT embed remote API calls that transmit note
  content as a side effect of normal operation.
- Metadata derived from notes (tags, backlinks, summaries) MUST be
  stored locally alongside the vault, not in external databases.
- If a future feature requires cloud sync or remote processing, it
  MUST be a separate, opt-in module with clear data-flow documentation.

**Rationale**: Personal notes contain private thoughts, credentials,
and sensitive information. Local-first is a trust guarantee.

### IV. Extensibility

- Tool definitions MUST be modular: each Obsidian plugin integration
  is a self-contained module with a declared interface (inputs, outputs,
  side effects).
- Adding a new tool MUST NOT require modifying existing tool modules.
  New tools register themselves; the system discovers them.
- Tool interfaces MUST follow a consistent contract: each tool declares
  its required vault permissions, the note fields it reads, and the
  note fields it writes.
- Configuration for tools MUST be declarative (e.g., YAML/JSON config)
  so users can enable, disable, or parameterize tools without code
  changes.

**Rationale**: The Obsidian ecosystem evolves rapidly. The system MUST
absorb new plugins without architectural changes.

### V. Idempotency

- Every automated operation MUST produce the same result whether
  executed once or multiple times against the same input state.
- Backlink insertion MUST check for existing links before adding.
  Running a backlink task twice on the same note MUST NOT create
  duplicate links.
- Tag and metadata operations MUST be set-based: adding a tag that
  already exists is a no-op, not a duplication.
- Operations MUST use content-aware guards (check-before-write) rather
  than blind appends. The guard logic MUST be part of the operation
  definition, not an optional wrapper.

**Rationale**: Users and automation will re-run tasks. The system
MUST be safe to retry without manual cleanup.

## Operational Constraints

- **Backup granularity**: Before any batch operation (3+ notes),
  the system MUST create a timestamped snapshot of affected files.
  Single-note operations MUST at minimum log the previous content
  hash for verification.
- **Conflict resolution**: If two operations target the same note
  concurrently, the second operation MUST detect the conflict (via
  content hash or timestamp check) and abort rather than overwrite.
- **Vault boundaries**: Operations MUST be scoped to a single vault.
  Cross-vault operations are not supported in the initial design.

## Development Workflow

- All new tool modules MUST include an idempotency test: run the
  operation twice and assert the output is identical both times.
- Data integrity violations (full-file overwrite without backup,
  duplicate link insertion) are treated as blocking defects.
- Privacy review: any new external dependency MUST be audited for
  data transmission before integration.
- Code review MUST verify that write operations use the narrowest
  available mutation API, per Principle II.

## Governance

- This constitution supersedes all other development practices for
  the Autonotes project. Conflicts between this document and other
  guidance MUST be resolved in favor of the constitution.
- Amendments require: (1) a written proposal describing the change
  and rationale, (2) review of impact on existing tools and data,
  (3) version bump per semantic versioning rules below.
- Version policy: MAJOR for principle removal or redefinition, MINOR
  for new principles or material expansions, PATCH for wording and
  clarification fixes.
- Compliance review: every PR MUST include a constitution check
  confirming no principle violations are introduced.

**Version**: 1.0.0 | **Ratified**: 2026-03-12 | **Last Amended**: 2026-03-12
