# Feature Specification: Vault Health Analytics

**Feature Branch**: `002-vault-health-analytics`
**Created**: 2026-03-12
**Status**: Draft
**Input**: User description: "Build a vault health analytics system that tracks orphan notes, tag distribution, backlink density, and cluster connectivity over time. Surface a dashboard endpoint with current metrics and historical trends. Integrate with the existing job system for scheduled scans."

## Clarifications

### Session 2026-03-12

- Q: What is the composite health score formula? → A: Weighted formula: backlink density 30%, orphan ratio 30%, cluster connectivity 25%, tag distribution 15%.
- Q: How does health analytics integrate with the existing system? → A: New job type (`vault_health_scan`) in the existing job system, reusing job service, deduplication, and progress tracking.
- Q: Where are health snapshots stored? → A: PostgreSQL table(s), consistent with existing jobs/logs storage.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Current Vault Health Metrics (Priority: P1)

As a vault owner, I want to request a snapshot of my vault's structural
health -- including orphan note count, tag distribution, backlink density,
and cluster connectivity -- so I can understand the current state of my
knowledge base at a glance.

**Why this priority**: This is the foundational capability. Without
computing and returning health metrics, no other feature (history,
dashboard, scheduling) has data to work with. Delivers immediate value
by answering "how healthy is my vault right now?"

**Independent Test**: Can be fully tested by triggering a health scan on
a vault with known structure (specific orphan notes, tag counts, link
patterns) and verifying the returned metrics match expected values.

**Acceptance Scenarios**:

1. **Given** a vault with 100 notes where 8 have no inbound backlinks,
   **When** the user requests a vault health scan, **Then** the system
   returns an orphan count of 8 and lists the orphan note paths.
2. **Given** a vault with notes using 25 distinct tags, **When** the user
   requests a vault health scan, **Then** the system returns a tag
   distribution showing each tag and its usage count, sorted by frequency.
3. **Given** a vault where notes average 3.2 backlinks per note, **When**
   the user requests a vault health scan, **Then** the system returns a
   backlink density metric (average links per note) and identifies notes
   with zero outbound links.
4. **Given** a vault with two disconnected clusters of notes (no links
   between them), **When** the user requests a vault health scan, **Then**
   the system reports 2 clusters with their respective note counts.

---

### User Story 2 - Track Health Metrics Over Time (Priority: P2)

As a vault owner, I want each health scan to be persisted so I can compare
metrics across time periods, identify trends (improving or degrading vault
health), and measure the impact of cleanup efforts.

**Why this priority**: Historical data transforms a one-time diagnostic
into an ongoing improvement tool. Without history, users cannot tell
whether their vault is getting better or worse over time.

**Independent Test**: Can be tested by running multiple scans at known
intervals, then querying historical data and verifying the returned
time-series matches the expected progression.

**Acceptance Scenarios**:

1. **Given** two health scans taken one week apart, **When** the user
   requests historical trends, **Then** the system returns both snapshots
   with timestamps and shows the delta for each metric.
2. **Given** ten historical snapshots over 30 days, **When** the user
   requests trends for a specific metric (e.g., orphan count), **Then**
   the system returns a time-series of that metric with one data point
   per snapshot.
3. **Given** no previous scans exist, **When** the user requests historical
   trends, **Then** the system returns an empty result set with a message
   indicating no history is available.

---

### User Story 3 - Dashboard Endpoint with Current and Historical Data (Priority: P3)

As a vault owner, I want a single dashboard endpoint that combines the
latest health metrics with historical trend summaries, so I have one place
to check vault health without making multiple requests.

**Why this priority**: A consolidated view is a convenience layer on top
of the scan (US1) and history (US2) capabilities. It reduces friction
but is not essential for core functionality.

**Independent Test**: Can be tested by verifying the dashboard endpoint
returns both current metrics and trend data in a single response, and
that the data matches what individual scan and history endpoints return.

**Acceptance Scenarios**:

1. **Given** at least one completed health scan exists, **When** the user
   requests the dashboard, **Then** the response includes the most recent
   scan results plus a trend summary covering the last 30 days.
2. **Given** the most recent scan is older than 24 hours, **When** the
   user requests the dashboard, **Then** the response includes a
   "stale_data" indicator with the age of the last scan.
3. **Given** no scans have been run, **When** the user requests the
   dashboard, **Then** the system returns a response indicating no data
   is available and suggests running an initial scan.

---

### User Story 4 - Scheduled Health Scans via Job System (Priority: P4)

As a vault owner, I want to schedule automatic health scans at a regular
interval (e.g., daily or weekly), so my vault health data stays current
without manual intervention.

**Why this priority**: Automation is valuable but depends on the scan
(US1) and storage (US2) being functional first. Users can always trigger
manual scans; scheduling is a convenience.

**Independent Test**: Can be tested by configuring a scheduled scan,
advancing time or waiting for the interval, and verifying a new scan
snapshot was created automatically.

**Acceptance Scenarios**:

1. **Given** a scheduled health scan configured for daily execution,
   **When** the scheduled time arrives, **Then** the system automatically
   runs a health scan and stores the results as a new snapshot.
2. **Given** a scheduled scan is already running, **When** the next
   scheduled interval triggers, **Then** the system skips the duplicate
   scan and logs that it was deferred.
3. **Given** a user wants to change the scan frequency, **When** they
   update the schedule configuration, **Then** subsequent scans follow
   the new interval.

---

### Edge Cases

- What happens when the vault is empty (zero notes)? The system MUST
  return valid metrics with zero values (0 orphans, 0 tags, 0 density,
  0 clusters) rather than an error.
- What happens when a note is deleted between the start and end of a
  scan? The system MUST skip the deleted note gracefully and report the
  scan as completed with a note about skipped files.
- What happens when the vault contains notes with no backlinks at all?
  The system MUST report a backlink density of 0.0 and flag all notes
  as orphans (except those explicitly linked from outside the scan scope).
- What happens when historical data exceeds storage limits? The system
  MUST retain the most recent 365 days of snapshots and automatically
  purge older entries.
- What happens when a scheduled scan overlaps with a manual scan? The
  system MUST use the existing job deduplication to prevent concurrent
  scans of the same scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute the following vault health metrics for
  a given scope (folder or entire vault): orphan note count (notes with
  zero inbound backlinks), tag distribution (each tag and its usage
  count), backlink density (average outbound links per note), and
  cluster connectivity (number of disconnected note groups).
- **FR-002**: System MUST identify and list orphan notes by path,
  distinguishing between notes with zero inbound links and notes with
  zero outbound links.
- **FR-003**: System MUST compute cluster connectivity using the vault's
  backlink graph, where two notes are in the same cluster if a path of
  links connects them (treating links as bidirectional for connectivity
  purposes).
- **FR-004**: System MUST persist each health scan result as a timestamped
  snapshot in PostgreSQL (consistent with existing jobs/logs storage),
  retaining snapshots for 365 days by default.
- **FR-005**: System MUST provide a historical query for any metric,
  returning a time-series of values across stored snapshots for a given
  date range.
- **FR-006**: System MUST expose a dashboard endpoint that returns the
  most recent scan results combined with trend summaries (delta from
  previous scan, 7-day and 30-day averages for each metric).
- **FR-007**: System MUST indicate when dashboard data is stale (last
  scan older than a configurable threshold, defaulting to 24 hours).
- **FR-008**: System MUST support scheduled health scans as a new
  `vault_health_scan` job type within the existing job system, reusing
  the job service, deduplication, and progress tracking infrastructure.
  Scans MUST be configurable at daily, weekly, or custom cron intervals.
- **FR-009**: Scheduled scans MUST use existing job deduplication to
  prevent concurrent scans of the same vault scope.
- **FR-010**: System MUST compute a single composite "vault health score"
  (0-100) using a weighted formula: backlink density (30%), orphan ratio
  (30%), cluster connectivity (25%), tag distribution (15%). Each
  sub-metric MUST be normalized to a 0-100 scale before weighting.
- **FR-011**: All scan operations MUST be scoped to a target folder path
  or the entire vault, consistent with existing scan behavior.

### Key Entities

- **HealthSnapshot**: A point-in-time record of vault health metrics.
  Attributes: snapshot ID, scan scope (folder path or vault root),
  timestamp, orphan count, orphan note paths, tag distribution map,
  backlink density (average), cluster count, cluster sizes, composite
  health score, total notes scanned.
- **HealthTrend**: A derived view over multiple snapshots for a single
  metric. Attributes: metric name, time range, data points (timestamp +
  value pairs), delta from previous, rolling averages.

## Assumptions

- The existing vault scan job infrastructure (Celery tasks, job service,
  deduplication) is available and functional.
- The existing note parser can extract backlinks and tags from notes,
  providing the raw data needed for metric computation.
- Orphan detection considers only notes within the scan scope (a note
  linked from outside the scope is still considered an orphan within
  that scope).
- Cluster connectivity treats wikilinks as bidirectional edges for graph
  traversal purposes (if A links to B, both are in the same cluster).
- A single user operates the system; no multi-tenant isolation is needed.
- The composite health score formula is deterministic and documented so
  users can understand why their score changed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can retrieve a complete vault health snapshot for a
  vault of 1000 notes within 60 seconds.
- **SC-002**: The dashboard endpoint returns current metrics and 30-day
  trends in a single request within 2 seconds.
- **SC-003**: Running the same health scan twice on an unchanged vault
  produces identical metric values both times.
- **SC-004**: Historical trend queries return time-series data for any
  metric spanning up to 365 days of snapshots within 1 second.
- **SC-005**: Scheduled scans execute within 5 minutes of their
  configured time without manual intervention.
- **SC-006**: The composite health score increases measurably after a
  user resolves orphan notes or adds missing backlinks identified by
  the scan.
