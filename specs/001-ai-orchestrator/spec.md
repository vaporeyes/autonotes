# Feature Specification: AI Orchestrator for Obsidian Vault Management

**Feature Branch**: `001-ai-orchestrator`
**Created**: 2026-03-12
**Status**: Draft
**Input**: User description: "Build an AI-Orchestrator that interfaces with the Obsidian Local REST API to read/analyze notes, perform surgical edits via domain-specific patch operations, execute Obsidian commands, manage long-running vault scans, and expose a monitoring UI."

## Clarifications

### Session 2026-03-12

- Q: What role does the LLM play in the orchestrator? → A: Full AI assistant -- summaries/embeddings for search, analysis to suggest backlinks/tags/cleanup targets, conversational interface for vault queries, and auto-action execution.
- Q: What does "Vault Cleanup" entail? → A: Fix structural issues -- orphaned backlinks (pointing to non-existent notes), duplicate/inconsistent tags, and missing standard frontmatter keys.
- Q: Do LLM-suggested changes auto-apply or require approval? → A: Risk-tiered -- low-risk changes (tag normalization, missing frontmatter) auto-apply; high-risk changes (backlink modifications, content changes) require explicit user approval.
- Q: What is the operation log retention policy? → A: 90 days default, configurable by the user.
- Q: Patch mechanism -- RFC 6902 or Obsidian-native? → A: Domain-specific patch operations (add-tag, add-backlink, update-frontmatter-key, append-body) as the orchestrator's API contract, translated internally to Obsidian's native PATCH headers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read and Analyze Vault Notes (Priority: P1)

As a vault owner, I want to point the orchestrator at a file or folder in
my vault and receive a parsed breakdown of its Markdown content and
frontmatter metadata, so I can understand what data is available before
running any automated edits.

**Why this priority**: Reading is the foundation for every other
capability. Without reliable parsing, surgical edits and backlink
operations cannot function. This delivers immediate value by letting
users inspect their vault programmatically.

**Independent Test**: Can be fully tested by requesting analysis of a
known note and verifying the parsed frontmatter keys, tags, and body
sections match the original file content.

**Acceptance Scenarios**:

1. **Given** a vault with a note containing YAML frontmatter and Markdown
   body, **When** the user requests analysis of that note by path,
   **Then** the system returns the frontmatter as structured key-value
   pairs and the body as a parsed Markdown tree (headings, lists, links).
2. **Given** a vault folder containing 10 notes, **When** the user
   requests analysis of the folder, **Then** the system returns a
   summary for each note including title, tags, backlink count, and
   word count.
3. **Given** a note path that does not exist, **When** the user requests
   analysis, **Then** the system returns a clear error indicating the
   file was not found without modifying any vault content.

---

### User Story 2 - Surgical Edit via Patch Operations (Priority: P2)

As a vault owner, I want to append backlinks, update tags, or modify
frontmatter metadata on a specific note using targeted patch operations,
so that only the intended fields change and the rest of the note remains
untouched.

**Why this priority**: This is the core value proposition. Once users can
read notes (P1), the next step is safely modifying them. Surgical edits
enforce the constitution's Data Integrity and Idempotency principles.

**Independent Test**: Can be tested by applying a patch to a known note,
then re-reading the note to confirm only the targeted fields changed
while the body and other frontmatter keys remain identical.

**Acceptance Scenarios**:

1. **Given** a note with frontmatter `tags: [daily, review]`, **When**
   the user submits a patch to add the tag `archived`, **Then** the
   frontmatter becomes `tags: [daily, review, archived]` and no other
   content in the note changes.
2. **Given** a note without a backlinks section, **When** the user
   submits a patch to append a backlink `[[ProjectNotes]]`, **Then** a
   backlinks section is added at the end of the note containing the link.
3. **Given** a note that already contains backlink `[[ProjectNotes]]`,
   **When** the same backlink patch is submitted again, **Then** the
   system does not create a duplicate link (idempotent no-op) and returns
   a response indicating no changes were made.
4. **Given** a patch operation on any note, **When** the operation begins,
   **Then** the system records a recoverable snapshot (content hash or
   backup) before applying the patch, and the operation log includes the
   file path, operation name, and timestamp.

---

### User Story 3 - Execute Obsidian Commands (Priority: P3)

As a vault owner, I want to trigger native Obsidian commands (such as
"Save current file" or "Insert template") through the orchestrator, so
that I can automate workflows that depend on Obsidian's built-in
functionality.

**Why this priority**: Command execution extends the orchestrator beyond
read/write into full workflow automation. It depends on the REST API
connection established in P1 and is less critical than the core
read/edit loop.

**Independent Test**: Can be tested by triggering a known Obsidian
command (e.g., "Save") and verifying the command executed successfully
via the API response status.

**Acceptance Scenarios**:

1. **Given** the Obsidian REST API is running and accessible, **When**
   the user triggers a valid command by name, **Then** the system
   forwards the command to Obsidian and returns the execution status.
2. **Given** a command name that does not exist in Obsidian, **When** the
   user triggers it, **Then** the system returns a descriptive error
   without executing any side effects.
3. **Given** the Obsidian REST API is unreachable, **When** the user
   triggers any command, **Then** the system returns a connection error
   within 5 seconds and does not retry silently.

---

### User Story 4 - Vault Scan with Task Queue (Priority: P4)

As a vault owner, I want to start a long-running vault scan (e.g.,
"find all notes missing backlinks") and track its progress, so that I
can monitor batch operations without blocking other work.

**Why this priority**: Vault-wide scans are valuable but not essential
for single-note workflows. This builds on P1 (read) and adds
operational infrastructure for batch processing.

**Independent Test**: Can be tested by starting a scan on a folder with
a known number of notes, polling for progress, and verifying the final
result matches expected counts.

**Acceptance Scenarios**:

1. **Given** a vault with 100 notes, **When** the user starts a "missing
   backlinks" scan, **Then** the system creates a trackable task,
   returns a task ID, and begins processing notes in the background.
2. **Given** an active scan task, **When** the user queries its status,
   **Then** the system returns current progress (notes processed / total)
   and estimated time remaining.
3. **Given** a completed scan task, **When** the user queries its result,
   **Then** the system returns the list of notes matching the scan
   criteria.
4. **Given** a scan is in progress, **When** the user requests a second
   identical scan, **Then** the system returns the existing task ID
   rather than starting a duplicate scan.

---

### User Story 5 - Monitoring UI and Manual Cleanup Jobs (Priority: P5)

As a vault owner, I want a web-based monitoring interface where I can
view agent operation logs and manually trigger "Vault Cleanup" jobs, so
that I have visibility into what the orchestrator has done and can run
maintenance tasks on demand.

**Why this priority**: The UI is a convenience layer on top of the core
capabilities. All operations are accessible via API first; the UI
provides discoverability and auditability.

**Independent Test**: Can be tested by opening the web interface,
verifying operation logs are visible, and triggering a cleanup job
through the UI controls.

**Acceptance Scenarios**:

1. **Given** the orchestrator is running, **When** the user opens the
   monitoring interface in a browser, **Then** they see a list of recent
   operations with timestamps, operation types, and affected file paths.
2. **Given** the monitoring interface is open, **When** the user clicks
   "Vault Cleanup", **Then** a cleanup task is created that scans for
   orphaned backlinks, duplicate/inconsistent tags, and missing standard
   frontmatter keys, and its progress is visible in the UI.
3. **Given** operation logs exist, **When** the user filters by operation
   type or date range, **Then** only matching log entries are displayed.

---

### Edge Cases

- What happens when the Obsidian REST API returns a malformed response
  (e.g., truncated JSON)? The system MUST treat this as a read error
  and not proceed with any write operations.
- What happens when a note's frontmatter is invalid YAML? The system
  MUST report the parse error and skip that note rather than corrupting
  it by attempting a write.
- What happens when a patch targets a frontmatter key that does not
  exist? The system MUST create the key (upsert behavior) without
  affecting other keys.
- What happens when two users trigger overlapping edits on the same
  note? The system MUST detect the conflict via content hash and abort
  the second operation per the constitution's Operational Constraints.
- What happens when a vault scan is interrupted (process crash)? Partial
  results MUST be recoverable, and re-running the scan MUST not produce
  duplicate entries in the results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST connect to the Obsidian Local REST API and
  verify connectivity before accepting any operations.
- **FR-002**: System MUST parse Markdown content into structured
  components (frontmatter, headings, body sections, links, tags).
- **FR-003**: System MUST support folder-level analysis, returning
  per-note summaries for all notes in a given path.
- **FR-004**: System MUST expose domain-specific patch operations
  (add-tag, add-backlink, update-frontmatter-key, append-body) as its
  API contract. Internally, these translate to the Obsidian REST API's
  native PATCH mechanism (heading-based targeting with custom headers).
- **FR-005**: Frontmatter patches MUST use key-level merge semantics
  (only changed keys are modified). Body patches MUST use targeted
  append/prepend/search-replace rather than full-file overwrite.
- **FR-006**: System MUST enforce idempotency on all write operations.
  Duplicate backlink insertions, tag additions, and metadata updates
  MUST be no-ops when the target state already matches.
- **FR-007**: System MUST create a recoverable snapshot (content hash
  or backup copy) before any write operation.
- **FR-008**: System MUST log every mutation with operation name,
  timestamp, and affected file path. Logs MUST be retained for 90
  days by default. Retention period MUST be user-configurable.
  Expired logs MUST be purged automatically.
- **FR-009**: System MUST forward Obsidian command execution requests
  to the REST API and return the result status.
- **FR-010**: System MUST support a task queue for long-running vault
  scans with progress tracking (processed count, total count).
- **FR-011**: System MUST prevent duplicate scans: if an identical scan
  is already running, return the existing task ID.
- **FR-012**: System MUST expose a web-based monitoring interface showing
  operation logs and providing manual job triggers.
- **FR-013**: System MUST scope all operations to a single vault. Cross-
  vault operations are not supported.
- **FR-014**: All note content MUST remain local by default. Note
  content may only be sent to an LLM provider when the user explicitly
  triggers an AI-powered operation (summary, suggestion, or chat query).
- **FR-015**: System MUST generate note summaries and embeddings via
  an LLM provider for semantic search and retrieval across the vault.
- **FR-016**: System MUST analyze note content via an LLM to suggest
  backlinks, tags, and cleanup targets. Changes MUST be classified as
  low-risk (tag normalization, missing frontmatter fill) or high-risk
  (backlink additions/removals, body content modifications). Low-risk
  changes auto-apply; high-risk changes require explicit user approval
  before being applied as patch operations.
- **FR-017**: System MUST support a conversational interface where
  users can ask natural-language questions about their vault content
  and receive answers grounded in their notes.
- **FR-018**: LLM payloads MUST be sent only to the configured
  provider endpoint. The system MUST log which notes were sent and
  when, as part of the operation log (FR-008).
- **FR-019**: Vault Cleanup MUST detect and report: (a) orphaned
  backlinks pointing to non-existent notes, (b) duplicate or
  inconsistent tags (e.g., #review vs #Review), and (c) notes
  missing required standard frontmatter keys. Low-risk fixes
  (tag normalization, frontmatter fill) auto-apply; high-risk
  fixes (orphaned backlink removal) require user approval.
  All applied changes MUST be logged per FR-008.

### Key Entities

- **Note**: A single Obsidian vault file. Attributes: file path,
  frontmatter (key-value metadata), body content, tags, backlinks,
  word count, last modified timestamp.
- **Patch Operation**: A targeted modification to a note. Attributes:
  target note path, operation type (add-tag, add-backlink,
  update-frontmatter-key, append-body), payload, idempotency key.
- **Vault Scan Task**: A long-running background job. Attributes: task
  ID, scan type, target folder, status (pending/running/completed/
  failed), progress (processed/total), result set, created timestamp.
- **Operation Log Entry**: An audit record. Attributes: timestamp,
  operation name, affected file path, before-hash, after-hash, status
  (success/failure/no-op), error message if applicable.
- **Obsidian Command**: A reference to a native Obsidian command.
  Attributes: command ID, display name, execution status.

## Assumptions

- The Obsidian Local REST API plugin is installed, configured, and
  running on the user's machine before the orchestrator starts.
- The REST API provides endpoints for reading file content, writing
  file content, listing files, and executing commands.
- The vault is stored on a local filesystem accessible to both Obsidian
  and the orchestrator process.
- Users interact with the orchestrator primarily through the API
  (Swagger/Redoc) interface; no desktop GUI is planned.
- A single user operates the orchestrator at a time. Multi-user
  concurrent access is out of scope for the initial version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can retrieve parsed frontmatter and body structure
  for any note in their vault within 2 seconds of request.
- **SC-002**: A folder scan of 500 notes completes and returns per-note
  summaries within 30 seconds.
- **SC-003**: Patch operations on a single note (add tag, add backlink,
  update metadata key) complete within 1 second.
- **SC-004**: Running any patch operation twice on the same note
  produces identical vault state both times (zero duplicate links,
  tags, or metadata entries).
- **SC-005**: Every write operation has a corresponding log entry
  viewable in the monitoring interface within 5 seconds of completion.
- **SC-006**: Users can trigger a "Vault Cleanup" job from the
  monitoring interface and track its progress to completion.
- **SC-007**: No note content leaves the user's local machine except
  when the user explicitly triggers an AI-powered operation (summary,
  suggestion, or chat query), in which case only the targeted note
  content is sent to the configured LLM provider.
- **SC-008**: If a write operation fails mid-execution, the affected
  note is left in its pre-operation state 100% of the time.
