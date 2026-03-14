# Quickstart: Web Dashboard

**Prerequisites**: Stack running (`docker compose up -d`), migrations applied (`docker compose exec api uv run alembic upgrade head`).

## 1. Open the dashboard

Navigate to http://localhost:8000/dashboard/ in a browser.

The System Dashboard view loads by default, showing:
- Service connectivity status (API, Obsidian, Redis, Postgres)
- Latest vault health metrics (if a health scan has been run)
- Trend sparklines for each metric

## 2. Trigger a health scan

If no health data exists, click "Run Health Scan" on the dashboard.

Monitor progress in the Jobs view (#/jobs) or watch the dashboard auto-refresh.

## 3. Browse notes

Navigate to Notes Browser (#/notes).

1. Click a folder in the tree on the left
2. Select a note from the list in the center
3. View its detail (frontmatter, headings, tags, backlinks) on the right
4. Click "Suggest Tags" or "Suggest Backlinks" to trigger AI analysis

## 4. Approve or reject patches

Navigate to Patches (#/patches).

Pending high-risk patches appear at the top. For each:
1. Review the target note, operation type, and payload
2. Click "Approve" or "Reject"
3. Confirm the action in the dialog

Completed patches appear in the collapsible history section.

## 5. Monitor jobs

Navigate to Jobs (#/jobs).

- Running jobs show progress bars that update every 5 seconds
- Filter by status or job type using the dropdowns
- Click "Cancel" on a running job to stop it
- Click a health scan job to see a link to its snapshot

## 6. Chat with the vault

Navigate to AI Chat (#/chat).

1. Optionally select a folder scope from the dropdown
2. Type a question in the input box
3. Press Enter or click Send
4. View the answer, source notes, and LLM provider
5. Previous messages remain visible in the conversation history

## 7. Review audit logs

Navigate to Logs (#/logs).

- Filter by target path or operation name
- Browse pages using Next/Previous buttons
- Each entry shows the operation, target path, status, and timestamp

## 8. Verify new API endpoints

```bash
# List pending patches
curl -s http://localhost:8000/api/v1/patches?status=pending_approval | jq

# Get vault folder structure
curl -s http://localhost:8000/api/v1/vault-structure | jq '.children[] | .name'
```
