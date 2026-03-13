# Feature Specification: Auto-Triage for Vault Notes

**Feature Branch**: `003-auto-triage`
**Created**: 2026-03-12
**Status**: Draft
**Input**: User description: "Build an auto-triage system that periodically scans recent notes and suggests missing tags, backlinks, and required frontmatter fields based on folder conventions. Low-risk fixes auto-apply through the existing patch system; suggestions for high-risk changes queue for approval."

## Clarifications

### Session 2026-03-12

- Q: How are backlink patterns expressed in conventions? -> A: As target folder paths (e.g., "must link to at least one note in `projects/`"). The system checks whether the note contains any `[[...]]` link pointing to a note within the specified folder.
- Q: How does convention inheritance handle conflicts? -> A: Additive with per-field override. Child folders inherit all parent rules and can override individual fields/tags/backlink targets. A child convention never silently drops parent requirements.
- Q: Are missing convention-defined tags low-risk or high-risk? -> A: Low-risk (auto-apply). The tag value is deterministic since it is specified in the convention. Only backlink additions are high-risk.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Folder Conventions (Priority: P1)

As a vault owner, I want to define conventions for each folder in my vault
(required frontmatter fields, expected tags, backlink patterns) so that
the system knows what a "complete" note looks like in each context.

**Why this priority**: Without conventions, the system has no rules to
triage against. This is the foundation for all automated detection and
remediation.

**Independent Test**: Can be fully tested by creating a convention
definition for a folder and verifying the system stores and retrieves it
correctly.

**Acceptance Scenarios**:

1. **Given** the user defines a convention for folder `projects/` requiring
   frontmatter fields `status` and `priority`, **When** the convention is
   saved, **Then** the system stores it and returns it on subsequent
   retrieval.
2. **Given** a convention exists for `projects/` and a sub-convention for
   `projects/active/`, **When** a note in `projects/active/` is triaged,
   **Then** the system applies the merged convention (parent rules plus
   child rules, with child overriding individual fields on conflict).
3. **Given** the user updates an existing convention, **When** the next
   triage scan runs, **Then** it uses the updated rules.

---

### User Story 2 - Scan Recent Notes and Detect Issues (Priority: P2)

As a vault owner, I want the system to periodically scan recently modified
notes and identify missing tags, absent frontmatter fields, and missing
backlinks based on the folder conventions, so that I am aware of
incomplete notes without manually checking each one.

**Why this priority**: Detection is the core value of auto-triage. Once
conventions exist (P1), scanning and surfacing issues delivers immediate
visibility into vault hygiene.

**Independent Test**: Can be tested by creating a note in a folder with
defined conventions, omitting a required field, running a triage scan,
and verifying the issue is reported.

**Acceptance Scenarios**:

1. **Given** a convention requires frontmatter field `status` in
   `projects/`, **When** a note in `projects/` lacks a `status` field
   and a triage scan runs, **Then** the system reports a "missing
   frontmatter field" issue for that note.
2. **Given** a convention expects tag `#project` on all notes in
   `projects/`, **When** a note in that folder lacks the tag and a
   triage scan runs, **Then** the system reports a "missing tag" issue.
3. **Given** a convention defines that notes in `meetings/` should
   backlink to at least one note in `projects/`, **When** a meeting note
   has no such backlink and a triage scan runs, **Then** the system
   reports a "missing backlink" issue.
4. **Given** a note that already satisfies all folder conventions,
   **When** a triage scan runs, **Then** no issues are reported for
   that note.

---

### User Story 3 - Auto-Apply Low-Risk Fixes (Priority: P3)

As a vault owner, I want low-risk fixes (adding missing frontmatter
fields with default values, normalizing tag casing) to be automatically
applied through the existing patch system, so that routine maintenance
happens without my intervention.

**Why this priority**: Auto-application of safe fixes is where the system
transitions from informational to actionable, reducing manual toil for
the vault owner.

**Independent Test**: Can be tested by creating a note missing a required
frontmatter field with a defined default value, running a triage scan,
and verifying the field was added to the note automatically.

**Acceptance Scenarios**:

1. **Given** a convention requires frontmatter field `status` with default
   value `draft` in `projects/`, **When** a note lacks that field and a
   triage scan runs, **Then** the system auto-applies a patch adding
   `status: draft` to the note's frontmatter.
2. **Given** a convention expects tag `#meeting` but a note has `#Meeting`,
   **When** a triage scan runs, **Then** the system auto-applies a tag
   normalization patch (case correction).
3. **Given** a low-risk fix is auto-applied, **When** the operation
   completes, **Then** the system logs the change in the operation log
   with the triage scan as the originating job.

---

### User Story 4 - Queue High-Risk Suggestions for Approval (Priority: P4)

As a vault owner, I want high-risk changes (adding backlinks, inserting
content) to be queued as pending patch operations that I can review and
approve or reject, so that I maintain control over substantive changes
to my notes.

**Why this priority**: This builds on the detection (P2) and auto-apply
(P3) foundation to handle the remaining change types safely, completing
the triage workflow.

**Independent Test**: Can be tested by triggering a triage scan that
detects a missing backlink, verifying the suggestion appears as a pending
patch operation, and approving or rejecting it.

**Acceptance Scenarios**:

1. **Given** a convention defines that `meetings/` notes should backlink
   to a project note, **When** a triage scan detects a missing backlink,
   **Then** the system creates a pending patch operation (not yet applied)
   with the suggested backlink.
2. **Given** a pending patch exists from a triage scan, **When** the user
   approves it, **Then** the patch is applied through the existing patch
   system and logged.
3. **Given** a pending patch exists from a triage scan, **When** the user
   rejects it, **Then** the patch is discarded and the rejection is
   logged.
4. **Given** a subsequent triage scan runs after a suggestion was rejected,
   **Then** the system does not re-suggest the same change for the same
   note until the note is modified again.

---

### User Story 5 - View Triage Results and History (Priority: P5)

As a vault owner, I want to view the results of triage scans including
detected issues, auto-applied fixes, and pending suggestions, so that I
have full visibility into what the system found and did.

**Why this priority**: Visibility and auditability are essential for trust
but depend on the core triage pipeline (P1-P4) being functional first.

**Independent Test**: Can be tested by running a triage scan and
retrieving the results, verifying all detected issues, applied fixes,
and pending suggestions are listed.

**Acceptance Scenarios**:

1. **Given** a triage scan has completed, **When** the user requests the
   scan results, **Then** the system returns a summary of issues found,
   fixes applied, and suggestions queued.
2. **Given** multiple triage scans have run over time, **When** the user
   queries triage history, **Then** results are listed in reverse
   chronological order with scan scope and issue counts.

---

### Edge Cases

- What happens when a note has invalid YAML frontmatter? The system MUST
  skip that note, report the parse error in the triage results, and
  continue scanning remaining notes.
- What happens when a folder has no convention defined? Notes in that
  folder MUST be skipped during triage with no issues reported.
- What happens when a convention references a frontmatter field with a
  default value but the note already has a different value for that field?
  The system MUST NOT overwrite the existing value; no issue is reported
  since the field is present.
- What happens when a note is modified between detection and auto-apply?
  The system MUST re-verify the note's current state before applying any
  patch and abort if the content has changed (content hash mismatch).
- What happens when the same triage scan is triggered while one is already
  running? The system MUST return the existing job ID rather than starting
  a duplicate scan (existing deduplication behavior).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a way to define folder conventions
  specifying required frontmatter fields (with optional default values),
  expected tags, and expected backlink patterns (expressed as target
  folder paths) for notes within a folder.
- **FR-002**: Folder conventions MUST support additive inheritance with
  per-field override: a sub-folder inherits all parent folder rules
  (required fields, tags, backlink targets) and may override individual
  entries. A child convention never silently drops parent requirements.
- **FR-003**: System MUST periodically scan recently modified notes
  (modified since the last successful triage scan) and compare them
  against their folder's conventions.
- **FR-004**: The triage scan schedule MUST be configurable by the user.
- **FR-005**: System MUST classify detected issues into risk tiers:
  low-risk (missing frontmatter fields with defaults, tag casing
  normalization, adding convention-defined expected tags) and high-risk
  (adding backlinks).
- **FR-006**: Low-risk fixes MUST be auto-applied through the existing
  patch system without user intervention.
- **FR-007**: High-risk suggestions MUST be queued as pending patch
  operations requiring explicit user approval before application.
- **FR-008**: All auto-applied fixes and queued suggestions MUST be
  logged in the operation log with the triage scan job as the source.
- **FR-009**: Rejected suggestions MUST be recorded so the system does
  not re-suggest the same change for the same note until the note is
  modified again.
- **FR-010**: System MUST expose triage scan results including: issues
  detected, fixes auto-applied, and suggestions pending approval.
- **FR-011**: System MUST verify note content has not changed (via
  content hash) between detection and patch application.
- **FR-012**: Triage scans MUST integrate with the existing job system
  for tracking, progress reporting, and deduplication.
- **FR-013**: System MUST support on-demand triage scans in addition to
  the periodic schedule, targeting a specific folder or the entire vault.

### Key Entities

- **Folder Convention**: A set of rules for a vault folder. Attributes:
  folder path, required frontmatter fields (with optional defaults),
  expected tags, expected backlink target folders (e.g., "must link to
  a note in `projects/`"), parent convention (for inheritance).
- **Triage Issue**: A detected deviation from a folder convention.
  Attributes: note path, issue type (missing-frontmatter, missing-tag,
  missing-backlink, tag-normalization), severity (low-risk, high-risk),
  convention reference, suggested fix.
- **Triage Scan Result**: The outcome of a single triage scan. Attributes:
  job reference, scan scope (folder path), notes scanned count, issues
  found count, fixes applied count, suggestions queued count, timestamp.

## Assumptions

- The existing patch system (patch_engine.py) handles idempotent
  application of add-tag, add-backlink, and update-frontmatter-key
  operations and is reused without modification.
- The existing approval workflow for pending patch operations is reused
  for high-risk triage suggestions.
- The existing job system (Celery task queue with progress tracking) is
  reused for triage scan execution.
- Folder conventions are managed via the API; there is no file-based
  convention format (e.g., `.vault-conventions.yml` inside the vault).
- "Recently modified" is determined by comparing note modification
  timestamps against the last successful triage scan timestamp.
- Folder conventions are stored in the database and managed via REST
  API endpoints (CRUD). This allows users to add, edit, and remove
  conventions at runtime without restarting services.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A triage scan of 500 recently modified notes completes
  within 60 seconds.
- **SC-002**: 100% of notes missing required frontmatter fields (with
  defaults) have the fields auto-added after a triage scan, with no
  manual intervention.
- **SC-003**: All high-risk suggestions appear as reviewable pending
  patches within 5 seconds of triage scan completion.
- **SC-004**: No auto-applied fix overwrites existing user-set values
  in note frontmatter or body content.
- **SC-005**: Rejected suggestions are not re-surfaced on subsequent
  scans unless the target note has been modified since rejection.
- **SC-006**: Every auto-applied fix and queued suggestion has a
  corresponding operation log entry traceable to the originating
  triage scan.
