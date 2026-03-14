# Research: Web Dashboard

## R1: Static File Serving Strategy

**Decision**: Use FastAPI's `StaticFiles` mount to serve the dashboard from `app/static/` at the `/dashboard` path. The API continues to be served at `/api/v1/`.

**Rationale**: FastAPI has built-in support for serving static files via `starlette.staticfiles.StaticFiles`. Mounting at `/dashboard` keeps the API namespace clean and avoids conflicts. The `html=True` option enables serving `index.html` as the default for directory requests, which supports the SPA pattern.

**Alternatives considered**:
- Nginx reverse proxy: Adds infrastructure complexity for a localhost-only tool. Rejected.
- Separate static file server: Contradicts the "no separate dev server" requirement. Rejected.
- Mount at root `/`: Would conflict with the `/api/v1` prefix and require careful ordering. Rejected.

## R2: Client-Side Routing Approach

**Decision**: Hash-based routing (`#/dashboard`, `#/notes`, `#/patches`, etc.) with a simple router in `app.js`.

**Rationale**: Hash-based routing works with static file serving without requiring server-side URL rewriting. The `hashchange` event is well-supported across all modern browsers. Each view registers a render function that the router calls when the hash changes.

**Alternatives considered**:
- History API (pushState): Requires server-side fallback to serve index.html for all routes. Adds complexity to FastAPI config. Rejected for a localhost tool.
- No routing (tab switching): Loses URL bookmarkability and browser back/forward. Rejected per SC-007.

## R3: Missing API Endpoints

**Decision**: Add two new read-only endpoints to support dashboard views.

### GET /patches (list patches by status)
The Patches & Approvals view needs to list pending patches and show history. No existing endpoint provides this. Add `GET /api/v1/patches` with query parameters: `status` (filter by patch status), `limit`, `offset`.

### GET /vault-structure (folder tree)
The Notes Browser needs a hierarchical folder tree. The existing `GET /notes/folder/{path}` returns notes in a single folder but not the folder hierarchy. Add `GET /api/v1/vault-structure` that returns a nested folder tree with note counts, built by recursively listing from the Obsidian API.

**Alternatives considered**:
- Client-side recursive folder fetching: Would require many sequential API calls (one per folder). Rejected for poor performance.
- Reuse existing folder endpoint with client-side tree building: Still requires multiple round-trips. Rejected.

## R4: Sparkline Rendering

**Decision**: Render sparklines as inline SVG elements using vanilla JavaScript. Each sparkline is a `<svg>` with a `<polyline>` plotting data points.

**Rationale**: SVG sparklines are lightweight (~20 lines of JS), require no external library, render crisply at any size, and are easy to style with CSS. The vault health trends API already returns time-series data points suitable for direct plotting.

**Alternatives considered**:
- Canvas-based rendering: Slightly more complex, doesn't scale as cleanly, harder to style. Rejected.
- Chart.js or similar library: Violates the "no external CDN" constraint and adds unnecessary weight for simple sparklines. Rejected.
- ASCII/text sparklines: Poor visual quality. Rejected.

## R5: Polling Strategy

**Decision**: Use `setInterval` with view-scoped cleanup. Each view that needs polling starts its own interval on mount and clears it on unmount (view change).

**Rationale**: Simple and reliable. The router calls a cleanup function before switching views, which clears any active polling intervals. Polling intervals: 5 seconds for job progress, 30 seconds for dashboard health refresh.

**Alternatives considered**:
- WebSocket: Server-sent events or WebSocket would provide real-time updates but require backend changes (new endpoint type). Overkill for a localhost single-user tool. Rejected.
- Long polling: More complex than simple polling with no meaningful benefit at localhost latency. Rejected.
