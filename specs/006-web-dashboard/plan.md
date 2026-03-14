# Implementation Plan: Web Dashboard

**Branch**: `006-web-dashboard` | **Date**: 2026-03-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-web-dashboard/spec.md`

## Summary

Add a lightweight web dashboard served as static files by the existing FastAPI backend. The SPA is built with vanilla HTML, CSS, and JavaScript (no frameworks, no build step) and provides 6 views: System Dashboard, Notes Browser, Patches & Approvals, Jobs Monitor, AI Chat, and Audit Logs. Two small backend additions are needed: a `GET /patches` endpoint for listing patches by status, and a `GET /vault-structure` endpoint for the folder tree. The frontend uses hash-based routing and the fetch() API for all backend communication.

## Technical Context

**Language/Version**: Python 3.12 (backend additions), HTML/CSS/JavaScript ES6+ (frontend)
**Primary Dependencies**: FastAPI (static file serving + 2 new endpoints), existing API routes
**Storage**: N/A (frontend is stateless; backend already has PostgreSQL)
**Testing**: Manual browser testing, curl for new endpoints
**Target Platform**: Modern desktop browsers (Chrome, Firefox, Safari)
**Project Type**: Single-page web application served by existing web service
**Performance Goals**: Dashboard load <3s, polling updates <5s latency
**Constraints**: No frameworks, no build step, no external CDN, vanilla JS only
**Scale/Scope**: 6 views, ~700 notes in vault, single user (localhost)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Data Integrity | PASS | Dashboard is read-only except for triggering existing endpoints (approve/reject/jobs). No new write paths to vault. All mutations go through existing patch_engine and job system. |
| II. Surgical Updates | PASS | No note modifications introduced. Approve/reject actions call existing endpoints that already follow surgical update principles. |
| III. Local-First Privacy | PASS | Dashboard is served locally. No external CDN, no analytics, no remote assets. All data stays on localhost. |
| IV. Extensibility | PASS | Frontend is modular (separate JS files per view). Adding new views requires adding a new JS module and nav link, not modifying existing views. |
| V. Idempotency | PASS | Dashboard makes only GET requests for data display. Action buttons (approve, reject, cancel) call existing idempotent endpoints. |

**Operational Constraints**:
- No new database tables or migrations required.
- Two new read-only API endpoints (GET /patches, GET /vault-structure) follow existing patterns.
- Static files served via FastAPI StaticFiles mount.

**Post-design re-check**: All principles remain satisfied. The dashboard introduces no new write paths, data storage, or privacy concerns.

## Project Structure

### Documentation (this feature)

```text
specs/006-web-dashboard/
  plan.md              # This file
  research.md          # Phase 0 output
  data-model.md        # Phase 1 output
  quickstart.md        # Phase 1 output
  contracts/
    api.md             # New API endpoints contract
    ui.md              # UI view contract
  checklists/
    requirements.md    # Spec quality checklist
  tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (changes to existing codebase)

```text
app/
  main.py                    # MODIFY: Mount static files directory
  api/routes/
    patches.py               # MODIFY: Add GET /patches list endpoint
    notes.py                 # MODIFY: Add GET /vault-structure endpoint
  static/                    # NEW: Static files directory
    index.html               # SPA entry point with nav shell
    css/
      styles.css             # Dark theme, layout, component styles
    js/
      app.js                 # Router, nav, shared utilities
      api.js                 # API client (fetch wrappers)
      views/
        dashboard.js         # System Dashboard view
        notes.js             # Notes Browser view
        patches.js           # Patches & Approvals view
        jobs.js              # Jobs Monitor view
        chat.js              # AI Chat view
        logs.js              # Audit Logs view
      components/
        sparkline.js         # SVG sparkline renderer
        progress-bar.js      # Job progress bar component
        folder-tree.js       # Folder tree component
```

**Structure Decision**: Static files live in `app/static/` adjacent to the existing backend code. JavaScript is organized by view (one file per SPA page) with shared components and API client. This keeps the frontend self-contained while being served by the same FastAPI process.
