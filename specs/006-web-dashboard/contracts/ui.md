# UI Contract: Web Dashboard

## SPA Shell (index.html)

The main HTML file provides:
- Navigation bar with links to all 6 views
- Active nav item highlighting based on current hash route
- A `<main id="app">` container where views render their content
- Viewport meta tag for responsive behavior

## Routes

| Hash Route    | View              | Default |
|---------------|-------------------|---------|
| #/dashboard   | System Dashboard  | Yes     |
| #/notes       | Notes Browser     |         |
| #/patches     | Patches           |         |
| #/jobs        | Jobs Monitor      |         |
| #/chat        | AI Chat           |         |
| #/logs        | Audit Logs        |         |

Unknown routes redirect to #/dashboard.

## View Contracts

### Dashboard View
- **Renders**: Service health indicators (4 services), vault metrics card, sparkline charts, stale-data warning banner, "Run Health Scan" button
- **Polls**: Every 30 seconds for health data refresh
- **API calls**: GET /health, GET /vault-health/dashboard, GET /vault-health/trends (per metric), POST /jobs (to trigger scan)

### Notes Browser View
- **Renders**: Left panel (folder tree), center panel (note list for selected folder), right panel (note detail for selected note)
- **Interactions**: Click folder to load notes, click note to load detail, AI analysis buttons in detail panel
- **API calls**: GET /vault-structure, GET /notes/folder/{path}, GET /notes/{path}, POST /ai/analyze

### Patches View
- **Renders**: Pending patches list (top), collapsible history section (bottom)
- **Interactions**: Approve/Reject buttons with confirmation dialog, expand/collapse history
- **API calls**: GET /patches?status=pending_approval, GET /patches (all statuses for history), POST /patches/{id}/approve, POST /patches/{id}/reject

### Jobs View
- **Renders**: Filterable job list with status badges, progress bars for running jobs, cancel button
- **Interactions**: Filter dropdowns (status, type), click to expand job details, cancel button
- **Polls**: Every 5 seconds when running jobs exist
- **API calls**: GET /jobs, GET /jobs/{id}, POST /jobs/{id}/cancel

### AI Chat View
- **Renders**: Chat message history (scrollable), input box, scope selector dropdown, send button
- **Interactions**: Type question, select scope folder, submit, click source note links
- **State**: Conversation history stored in JS array (cleared on page reload)
- **API calls**: POST /ai/chat

### Audit Logs View
- **Renders**: Table with columns (target path, operation, status, timestamp), filter inputs, pagination controls
- **Interactions**: Filter by target path or operation name, navigate pages
- **API calls**: GET /logs

## Shared Components

### Sparkline
- Input: Array of {timestamp, value} data points
- Output: SVG element with polyline

### Progress Bar
- Input: current (number), total (number)
- Output: Styled div with percentage fill and label

### Folder Tree
- Input: VaultStructureNode tree
- Output: Nested collapsible list with click handlers
- Behavior: Clicking a folder fires a callback; expanded state is maintained in memory

## Design Tokens (CSS Custom Properties)

```css
--bg-primary: #1a1a2e
--bg-secondary: #16213e
--bg-card: #1e2a3a
--text-primary: #e0e0e0
--text-secondary: #a0a0a0
--accent: #4fc3f7
--accent-hover: #81d4fa
--success: #66bb6a
--warning: #ffa726
--error: #ef5350
--border: #2a3a4a
--font-mono: 'SF Mono', 'Fira Code', monospace
--font-sans: 'Inter', -apple-system, sans-serif
--radius: 6px
--spacing-sm: 8px
--spacing-md: 16px
--spacing-lg: 24px
```
