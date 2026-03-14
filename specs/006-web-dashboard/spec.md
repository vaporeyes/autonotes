# Feature Specification: Web Dashboard

**Feature Branch**: `006-web-dashboard`
**Created**: 2026-03-14
**Status**: Draft
**Input**: User description: "Build a lightweight web dashboard for the Autonotes API"

## User Scenarios & Testing

### User Story 1 - System Dashboard (Priority: P1)

A user opens the dashboard landing page and sees the overall system health at a glance: connectivity status for API, Obsidian, Redis, and Postgres; the latest vault health snapshot (health score, orphan count, backlink density, cluster count, tag count); and trend sparklines for each metric over recent snapshots. If the last health scan is stale, a warning is shown. The user can trigger a new health scan directly from this page.

**Why this priority**: The dashboard is the entry point and provides immediate value by surfacing system status and vault health without requiring API knowledge or curl commands.

**Independent Test**: Navigate to the dashboard URL and verify health status indicators display, vault metrics render, and the "Run Scan" button triggers a health scan job.

**Acceptance Scenarios**:

1. **Given** the stack is running and a health snapshot exists, **When** the user opens the dashboard, **Then** they see connectivity indicators (green/red) for each service and the latest vault health metrics.
2. **Given** multiple health snapshots exist, **When** the dashboard loads, **Then** sparkline charts show metric trends across recent snapshots.
3. **Given** the last health scan was more than 24 hours ago, **When** the dashboard loads, **Then** a stale-data warning is displayed.
4. **Given** the user clicks "Run Health Scan", **When** the scan job is submitted, **Then** the UI shows the job status and polls for completion.

---

### User Story 2 - Notes Browser (Priority: P2)

A user browses the vault structure through a folder tree on the left side. Selecting a folder loads a list of notes showing title, tags, backlink count, and word count. Selecting a note displays its parsed frontmatter, headings outline, tags, backlinks, and content hash. From the note detail view, the user can trigger AI analysis (suggest backlinks, suggest tags, generate summary).

**Why this priority**: Browsing and inspecting notes is the core interaction for understanding vault content and is a prerequisite for meaningful use of patches and AI features.

**Independent Test**: Open the Notes Browser, expand folder tree, select a folder to see its notes, select a note to see its detail, and trigger an AI analysis action.

**Acceptance Scenarios**:

1. **Given** the vault has folders, **When** the user opens Notes Browser, **Then** a folder tree is rendered from the vault structure.
2. **Given** a folder is selected, **When** the folder loads, **Then** a list of notes in that folder is displayed with title, tags, backlink count, and word count.
3. **Given** a note is selected, **When** the detail panel loads, **Then** parsed frontmatter, headings, tags, backlinks, and content hash are shown.
4. **Given** a note is selected, **When** the user clicks "Suggest Tags", **Then** an AI analysis request is submitted and results are displayed.

---

### User Story 3 - Patches and Approvals (Priority: P3)

A user views pending high-risk patches that require approval. Each pending patch shows the target note, operation type, and payload. The user can approve or reject each patch with a confirmation step. Completed and rejected patches are shown in a collapsible history section below the pending list.

**Why this priority**: Patch approval is a critical workflow for maintaining vault integrity and is essential for the risk-tiered approval system to function through the UI.

**Independent Test**: View pending patches list, approve one patch, reject another, and verify both appear in the history section.

**Acceptance Scenarios**:

1. **Given** pending patches exist, **When** the user opens Patches view, **Then** a list of pending patches is displayed with target note, operation type, and payload.
2. **Given** a pending patch is shown, **When** the user clicks "Approve" and confirms, **Then** the patch is approved and moves to history.
3. **Given** a pending patch is shown, **When** the user clicks "Reject" and confirms, **Then** the patch is rejected and moves to history.
4. **Given** completed/rejected patches exist, **When** the user expands the history section, **Then** past patches are shown with their final status.

---

### User Story 4 - Jobs Monitor (Priority: P4)

A user views a list of background jobs with their status, progress bars for running jobs, and a cancel button for active jobs. Jobs can be filtered by status and type. Clicking a job shows its details, and for health scan jobs, links to the resulting snapshot.

**Why this priority**: Monitoring background jobs provides visibility into long-running operations (batch patches, health scans, embedding jobs) and allows cancellation of unwanted jobs.

**Independent Test**: View jobs list, filter by status, observe a running job's progress bar updating via polling, cancel a job, and click a health scan job to see its snapshot link.

**Acceptance Scenarios**:

1. **Given** jobs exist, **When** the user opens Jobs view, **Then** a list of jobs is displayed with status, type, and timestamps.
2. **Given** a job is running, **When** the view renders, **Then** a progress bar shows current progress and polls for updates.
3. **Given** a running job exists, **When** the user clicks "Cancel", **Then** the job is cancelled and status updates.
4. **Given** filters are available, **When** the user selects a status filter, **Then** only jobs with that status are shown.
5. **Given** a completed health scan job, **When** the user clicks it, **Then** the job detail includes a link to the health snapshot.

---

### User Story 5 - AI Chat (Priority: P5)

A user interacts with a chat interface to ask questions about the vault. The chat maintains a scrollable conversation history within the browser session (cleared on page reload), showing all previous questions and answers. Each response shows the answer, source notes referenced, and the LLM provider used. A scope selector allows limiting queries to a specific folder.

**Why this priority**: AI chat provides intelligent vault exploration but depends on other features (notes, embeddings) being accessible first.

**Independent Test**: Open AI Chat, type a question, receive an answer with source note references, and use the scope selector to limit to a folder.

**Acceptance Scenarios**:

1. **Given** the chat interface is open, **When** the user types a question and submits, **Then** an answer is displayed with source notes and LLM provider.
2. **Given** the scope selector is set to a specific folder, **When** the user asks a question, **Then** the query is scoped to that folder.
3. **Given** a chat response is received, **When** source notes are listed, **Then** each source note is clickable and navigates to the Notes Browser detail.

---

### User Story 6 - Audit Logs (Priority: P6)

A user views a filterable audit trail table showing target path, operation name, status, and timestamp. The table supports pagination for browsing large log histories.

**Why this priority**: Logs provide transparency and accountability but are primarily a reference tool used less frequently than active management features.

**Independent Test**: Open Logs view, see paginated log entries, apply filters by target path or operation, and navigate between pages.

**Acceptance Scenarios**:

1. **Given** operation logs exist, **When** the user opens Logs view, **Then** a table of log entries is displayed with target path, operation, status, and timestamp.
2. **Given** filters are available, **When** the user filters by target path, **Then** only matching entries are shown.
3. **Given** more logs than one page, **When** the user clicks "Next", **Then** the next page of results is displayed.

---

### Edge Cases

- What happens when the API is unreachable? The dashboard shows a connection error banner and retries periodically.
- What happens when no health snapshots exist? The dashboard shows a "No data yet" message with a prompt to run a health scan.
- What happens when a folder has no notes? The Notes Browser shows an empty state message.
- What happens when AI analysis fails (LLM unavailable)? An error message is shown inline without crashing the UI.
- What happens when the user navigates between views during a polling operation? Polling stops for the previous view and starts for the new view if needed.

## Requirements

### Functional Requirements

- **FR-001**: System MUST serve the dashboard as a single-page application via static files from the existing backend, requiring no separate dev server or build step.
- **FR-002**: System MUST display real-time connectivity status for API, Obsidian, Redis, and Postgres services on the dashboard landing page.
- **FR-003**: System MUST display the latest vault health snapshot metrics (health score, orphan count, backlink density, cluster count, tag count) on the dashboard.
- **FR-004**: System MUST render trend sparklines for vault health metrics using recent snapshot history.
- **FR-005**: System MUST warn users when the last health scan is older than 24 hours.
- **FR-006**: System MUST provide a folder tree navigation for browsing vault structure in the Notes Browser.
- **FR-007**: System MUST display note metadata (title, tags, backlink count, word count) when a folder is selected.
- **FR-008**: System MUST display parsed note detail (frontmatter, headings, tags, backlinks, content hash) when a note is selected.
- **FR-009**: System MUST allow triggering AI analysis actions (suggest backlinks, suggest tags, generate summary) from the note detail view.
- **FR-010**: System MUST display pending high-risk patches with approve/reject actions and a confirmation step.
- **FR-011**: System MUST show completed and rejected patches in a collapsible history section.
- **FR-012**: System MUST display background jobs with status, progress bars for running jobs, and cancel functionality.
- **FR-013**: System MUST support filtering jobs by status and type.
- **FR-014**: System MUST provide a chat interface for vault questions that maintains a scrollable conversation history within the browser session (cleared on page reload), displaying answers, source notes, and LLM provider for each exchange.
- **FR-015**: System MUST support a scope selector to limit AI chat queries to a specific folder.
- **FR-016**: System MUST display a paginated, filterable audit log table.
- **FR-017**: System MUST use polling to update progress for running jobs and health scans.
- **FR-018**: All API calls MUST use relative paths (/api/v1/...) via the fetch() API.
- **FR-019**: System MUST use a clean, minimal dark theme design that is responsive but desktop-primary.
- **FR-020**: System MUST implement client-side routing for navigation between views without full page reloads.

### Key Entities

- **View**: A distinct page/section of the SPA (Dashboard, Notes Browser, Patches, Jobs, AI Chat, Logs), each with its own URL hash route.
- **Health Status**: Connectivity state for each backend service, derived from the /health API endpoint.
- **Vault Snapshot**: A point-in-time capture of vault health metrics, retrieved from the vault health API.
- **Note**: A vault document with metadata (frontmatter, tags, backlinks, word count) browsable through the folder tree.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can view system health status and vault metrics within 3 seconds of opening the dashboard.
- **SC-002**: Users can navigate from the folder tree to a note's full detail view in 2 clicks or fewer.
- **SC-003**: Users can approve or reject a pending patch in 3 clicks or fewer (select, action, confirm).
- **SC-004**: Running job progress updates are visible within 5 seconds of a status change.
- **SC-005**: Users can submit an AI chat question and see the response without leaving the chat view.
- **SC-006**: The entire dashboard loads as a single page with no build step, framework dependency, or external CDN requirement.
- **SC-007**: All 6 views are accessible via distinct URL routes, enabling direct linking and browser back/forward navigation.

## Clarifications

### Session 2026-03-14

- Q: Should the AI Chat view maintain a scrollable conversation history within the browser session, or show only the most recent Q&A? → A: Scrollable conversation history within the browser session (cleared on page reload).

## Assumptions

- The existing FastAPI backend serves static files from a configured directory (or can be configured to do so).
- All required API endpoints already exist (health, notes, patches, jobs, AI chat, logs, vault health).
- Sparklines are rendered using lightweight inline SVG or canvas elements, not a charting library.
- The dark theme uses CSS custom properties for consistent theming.
- Hash-based routing (#/dashboard, #/notes, #/patches, etc.) is used for client-side navigation.
- Polling intervals are 5 seconds for job progress and 30 seconds for dashboard health refresh.
