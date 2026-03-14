# API Contract: Web Dashboard

## New Endpoints

### GET /api/v1/patches

List patch operations with optional filtering by status.

**Query Parameters**:

| Parameter | Type   | Required | Default | Description                              |
|-----------|--------|----------|---------|------------------------------------------|
| status    | string | no       | null    | Filter by status (pending_approval, applied, skipped, reverted, failed) |
| limit     | int    | no       | 50      | Max results (1-500)                      |
| offset    | int    | no       | 0       | Pagination offset                        |

**Response** (200):
```json
{
  "patches": [
    {
      "patch_id": "uuid",
      "job_id": "uuid",
      "target_path": "00 Fleeting/note.md",
      "operation_type": "add_backlink",
      "payload": {"target": "other-note.md"},
      "status": "pending_approval",
      "risk_level": "high",
      "created_at": "2026-03-14T12:00:00Z",
      "applied_at": null
    }
  ],
  "total": 5
}
```

### GET /api/v1/vault-structure

Return hierarchical folder tree of the vault.

**Query Parameters**: None

**Response** (200):
```json
{
  "name": "/",
  "path": "/",
  "note_count": 3,
  "children": [
    {
      "name": "00 Fleeting",
      "path": "00 Fleeting/",
      "note_count": 12,
      "children": []
    },
    {
      "name": "10 Literature",
      "path": "10 Literature/",
      "note_count": 8,
      "children": [
        {
          "name": "Books",
          "path": "10 Literature/Books/",
          "note_count": 5,
          "children": []
        }
      ]
    }
  ]
}
```

## Existing Endpoints Used by Dashboard

All existing endpoints are consumed as-is. No modifications needed.

| Endpoint                          | Used By          | Method |
|-----------------------------------|------------------|--------|
| /api/v1/health                    | Dashboard        | GET    |
| /api/v1/vault-health/dashboard    | Dashboard        | GET    |
| /api/v1/vault-health/trends       | Dashboard        | GET    |
| /api/v1/notes/folder/{path}       | Notes Browser    | GET    |
| /api/v1/notes/{path}              | Notes Browser    | GET    |
| /api/v1/patches/{id}/approve      | Patches          | POST   |
| /api/v1/patches/{id}/reject       | Patches          | POST   |
| /api/v1/jobs                      | Jobs, Dashboard  | GET    |
| /api/v1/jobs/{id}                 | Jobs             | GET    |
| /api/v1/jobs/{id}/cancel          | Jobs             | POST   |
| /api/v1/jobs                      | Dashboard        | POST   |
| /api/v1/ai/chat                   | AI Chat          | POST   |
| /api/v1/ai/analyze                | Notes Browser    | POST   |
| /api/v1/logs                      | Audit Logs       | GET    |
