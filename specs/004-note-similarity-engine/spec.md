# Feature Specification: Note Similarity Engine

**Feature Branch**: `004-note-similarity-engine`
**Created**: 2026-03-13
**Status**: Draft
**Input**: User description: "Build an embeddings-based note similarity engine that detects near-duplicate notes and clusters related notes. Expose a similarity search endpoint and a MOC (Map of Content) generator that drafts a new note linking clustered notes together."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find Similar Notes (Priority: P1)

As a vault owner, I want to search for notes similar to a given note so I can discover related content I may have forgotten about and identify near-duplicates worth merging or cleaning up.

I select a note (by path) and request similar notes. The system returns a ranked list of notes ordered by similarity, each with a similarity score and a brief reason (shared topics, overlapping content). I can set a minimum similarity threshold to filter noise.

**Why this priority**: Similarity search is the core capability. Without embeddings and search, no other feature (duplicates, clusters, MOC generation) can work. This also delivers immediate standalone value -- users can discover forgotten related notes.

**Independent Test**: Can be fully tested by embedding a set of notes, querying for similar notes to a known note, and verifying the results are semantically relevant. Delivers value as a standalone discovery tool.

**Acceptance Scenarios**:

1. **Given** a vault with embedded notes, **When** I request notes similar to `20 Permanent/Architecture/Cloud/microservices-patterns.md`, **Then** I receive a ranked list of related notes with similarity scores between 0.0 and 1.0, ordered by descending similarity.
2. **Given** a vault with embedded notes, **When** I request similar notes with a minimum threshold of 0.8, **Then** only notes meeting or exceeding that threshold are returned.
3. **Given** a note that has not been embedded yet, **When** I request similar notes for it, **Then** the system embeds it on-the-fly before searching and includes it in future searches.
4. **Given** a vault where no notes have been embedded, **When** I request similar notes, **Then** the system returns an informative message indicating that an embedding job should be run first.
5. **Given** a vault with embedded notes, **When** I submit a free-text query like "kubernetes deployment strategies", **Then** I receive a ranked list of notes whose content is semantically similar to the query text.

---

### User Story 2 - Detect Near-Duplicate Notes (Priority: P2)

As a vault owner, I want to detect near-duplicate notes across my vault so I can identify redundant content that should be merged, archived, or deleted. Near-duplicates are note pairs whose similarity exceeds a configurable high-similarity threshold (default: 0.9).

**Why this priority**: Duplicate detection is a direct extension of similarity search (same embeddings, different query) and addresses a common pain point in large vaults -- content sprawl with overlapping notes.

**Independent Test**: Can be tested by running a duplicate detection scan on a vault with known duplicate content and verifying the pairs are surfaced with their similarity scores.

**Acceptance Scenarios**:

1. **Given** a vault with embedded notes including two notes covering the same topic, **When** I run a duplicate detection scan, **Then** the system returns a list of note pairs with similarity above the threshold.
2. **Given** a duplicate detection scan result, **When** I view the results, **Then** each pair shows both note paths, their similarity score, and a short excerpt from each note for quick comparison.
3. **Given** a vault with no near-duplicates above the threshold, **When** I run duplicate detection, **Then** the system returns an empty result set.

---

### User Story 3 - Cluster Related Notes (Priority: P3)

As a vault owner, I want the system to automatically group my notes into topic clusters so I can see how my knowledge is organized and discover gaps or unexpected connections.

The system groups embedded notes into clusters of related content. Each cluster has a label (derived from the most common tags or a representative note title) and a list of member notes.

**Why this priority**: Clustering builds on the same embedding data but adds analytical value. It provides a vault-wide structural view rather than single-note queries.

**Independent Test**: Can be tested by running a clustering job on embedded notes and verifying that topically related notes (e.g., all AWS notes, all fitness notes) are grouped together.

**Acceptance Scenarios**:

1. **Given** a vault with embedded notes spanning multiple topics, **When** I run a clustering job, **Then** the system produces distinct clusters where notes within each cluster share topical similarity.
2. **Given** a clustering result, **When** I view the clusters, **Then** each cluster shows a label, the number of member notes, and the list of note paths.
3. **Given** a vault where some notes don't fit any cluster well, **Then** those notes are placed in an "unclustered" group rather than being forced into a poor-fit cluster.

---

### User Story 4 - Generate MOC from Cluster (Priority: P4)

As a vault owner, I want to generate a Map of Content (MOC) note from a cluster so I can create navigational hub notes that link related content together, improving vault structure.

When I select a cluster, the system drafts a new Markdown note containing a title, a brief description of the cluster's theme, and wiki-style links (`[[note path]]`) to all member notes, grouped by sub-topic where possible. The MOC is created as a draft that I can review and edit before it is written to the vault.

**Why this priority**: MOC generation is the highest-value output of clustering but depends on clusters existing first. It transforms analytical data into actionable vault improvements.

**Independent Test**: Can be tested by generating a MOC from a known cluster and verifying the output contains valid wiki-links to all cluster members in well-structured Markdown.

**Acceptance Scenarios**:

1. **Given** a cluster of 10 related notes, **When** I request a MOC for that cluster, **Then** the system generates a Markdown document with a descriptive title, summary paragraph, and `[[wiki-links]]` to all 10 notes.
2. **Given** a generated MOC draft, **When** I approve it, **Then** the note is written to a configurable target folder in the vault (default: `30 Maps/`).
3. **Given** a generated MOC draft, **When** I reject it, **Then** no note is written and the draft is discarded.
4. **Given** a cluster where a MOC already exists for the same topic, **When** I generate a new MOC, **Then** the system warns that a similar MOC may already exist and shows the existing note path.

---

### User Story 5 - Embed Vault Notes (Priority: P5)

As a vault owner, I want to run a background job that embeds all (or a scoped subset of) my vault notes so the similarity engine has data to work with. Re-running the job should only embed notes that are new or modified since the last run.

**Why this priority**: While embedding is a prerequisite for all other features, it is listed as P5 because it is infrastructure -- the user interacts with it once (or on a schedule) and then uses the higher-value search/cluster/MOC features daily. It will be built first but tested last as a standalone story.

**Independent Test**: Can be tested by running an embedding job, verifying embeddings are stored, modifying a note, re-running the job, and verifying only the modified note is re-embedded.

**Acceptance Scenarios**:

1. **Given** a vault with 500 notes, **When** I trigger an embedding job for the full vault, **Then** the system processes all notes and reports progress (current/total).
2. **Given** a previous embedding run completed, **When** I modify 3 notes and trigger a new embedding job, **Then** only those 3 notes are re-embedded (incremental update).
3. **Given** an embedding job in progress, **When** I check the job status, **Then** I see progress (e.g., 150/500 notes embedded).
4. **Given** a note in `100 Archive/` or `90 Atlas/Templates/`, **When** an embedding job runs with default scope, **Then** template notes are excluded from embedding (configurable exclusion patterns).

---

### Edge Cases

- What happens when a note is empty or contains only frontmatter? The system skips it during embedding and excludes it from similarity results.
- What happens when a note is deleted between embedding and search? The system returns results excluding the deleted note and marks its embedding as stale for cleanup.
- What happens when the vault contains binary files or non-Markdown files? The system only processes `.md` files and ignores all others.
- What happens when two notes are exact duplicates (similarity = 1.0)? They are flagged as exact duplicates in the duplicate detection results with a distinct label.
- What happens when the embedding provider is unavailable? The embedding job fails gracefully, reports the error, and can be retried. Previously stored embeddings remain valid.
- What happens when a MOC is generated for a cluster with only 1 note? The system rejects the request with a message that a MOC requires at least 2 notes.
- How does the system handle very large notes (e.g., 10,000+ words)? Notes exceeding the embedding provider's token limit are truncated to fit, with a warning logged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate vector embeddings for vault note content (body text, excluding raw frontmatter YAML)
- **FR-002**: System MUST store embeddings persistently and associate each embedding with its source note path and a content hash for staleness detection
- **FR-003**: System MUST support incremental embedding -- only re-embed notes whose content hash has changed since the last embedding run
- **FR-004**: System MUST provide a similarity search endpoint that accepts either a note path or a free-text query and returns ranked similar notes with scores
- **FR-005**: System MUST support a configurable similarity threshold for filtering search results (default: 0.5)
- **FR-006**: System MUST provide a duplicate detection scan that identifies note pairs exceeding a high-similarity threshold (default: 0.9)
- **FR-007**: System MUST cluster embedded notes into topic groups using their embedding vectors
- **FR-008**: System MUST assign a human-readable label to each cluster derived from member note metadata (tags, titles, or folder paths)
- **FR-009**: System MUST generate a MOC (Map of Content) Markdown draft from a selected cluster, containing wiki-links to all member notes
- **FR-010**: System MUST write approved MOC drafts to the vault through the existing patch system with content hash verification
- **FR-011**: System MUST support configurable exclusion patterns to skip certain folders or note patterns from embedding (default: templates, attachments)
- **FR-012**: System MUST run embedding and clustering as background jobs with progress tracking through the existing job system
- **FR-013**: System MUST log all embedding operations (note paths sent, tokens consumed) for privacy auditing, consistent with existing LLM interaction logging. Triggering an embedding job or similarity search constitutes explicit user consent for sending note content to the embedding provider.
- **FR-014**: System MUST embed a note on-the-fly when similarity is requested for a note that has not yet been embedded. The resulting embedding MUST be persisted so the note is included in future searches without re-computation.

### Key Entities

- **NoteEmbedding**: Represents a stored vector embedding for a single note. Key attributes: note path, content hash, embedding vector, token count, embedded timestamp. One embedding per note (latest version).
- **SimilarityResult**: Represents a pair of notes with a computed similarity score. Used in both search results and duplicate detection. Attributes: source note path, target note path, similarity score (0.0-1.0).
- **NoteCluster**: Represents a group of topically related notes. Attributes: cluster label, member note paths, centroid vector, creation timestamp. Created by clustering jobs.
- **MOCDraft**: Represents a generated Map of Content waiting for approval. Attributes: target path, Markdown content, source cluster reference, approval status. Follows the existing pending-approval pattern.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Similarity search returns results within 3 seconds for vaults up to 1,000 notes
- **SC-002**: Full vault embedding job processes at least 100 notes per minute
- **SC-003**: Duplicate detection identifies note pairs with 90%+ content overlap with at least 85% precision (fewer than 15% false positives)
- **SC-004**: Generated MOC notes contain valid wiki-links to all cluster member notes with no broken links
- **SC-005**: Incremental re-embedding processes only changed notes, reducing repeat job duration by at least 80% compared to full re-embedding
- **SC-006**: Users can discover related notes they were previously unaware of (validated by finding at least 3 non-obvious connections in a 500+ note vault)

## Clarifications

### Session 2026-03-13

- Q: Which embedding provider should the system use? → A: OpenAI embeddings only (e.g., text-embedding-3-small). Single provider, no abstraction layer needed.
- Q: Should similarity search support free-text queries in addition to note paths? → A: Yes. Accept a text query as an alternative to a note path -- embed the query string and search the same vector space.
- Q: What is the privacy consent model for sending note content to the embedding provider? → A: Triggering an embedding job or similarity search is the explicit user action (same pattern as POST /ai/analyze). No additional consent step needed.

## Assumptions

- The vault owner has an active OpenAI API key (embeddings use OpenAI exclusively; the existing OpenAI provider configuration is reused)
- The existing job system (Celery + Redis) is sufficient for embedding and clustering background work
- Note content is primarily English text; multi-language support is out of scope for this iteration
- The vault contains fewer than 10,000 notes; scaling beyond that is a future concern
- MOC generation uses the LLM for summarization/labeling; raw clustering uses only vector math
- The existing `30 Maps/` folder is the default target for generated MOCs, matching the vault's Zettelkasten structure
- Embedding vectors are stored in the database alongside note metadata, not in a separate vector store (sufficient for vaults under 10,000 notes)

## Out of Scope

- Real-time embedding on note save (embedding is triggered manually or on schedule)
- Cross-vault similarity (comparing notes across different Obsidian vaults)
- Semantic search by conversational natural-language questions (the free-text query finds similar notes, it does not answer questions)
- Automatic merging or deletion of duplicate notes
- Multi-language embedding or translation
