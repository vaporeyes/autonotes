# Data Model: Web Dashboard

## Entity Changes

No new database entities or migrations required. The dashboard is a read-only frontend that consumes existing API endpoints.

## New API Response Schemas

### New: VaultStructureNode (Pydantic schema only)

Represents a folder in the vault hierarchy for the folder tree component.

| Field       | Type                      | Description                                    |
|-------------|---------------------------|------------------------------------------------|
| name        | string                    | Folder display name                            |
| path        | string                    | Full folder path in vault                      |
| note_count  | int                       | Number of .md files directly in this folder    |
| children    | list[VaultStructureNode]  | Nested subfolders                              |

### New: PatchListItem (Pydantic schema only)

Represents a patch operation in the list view.

| Field          | Type           | Description                                          |
|----------------|----------------|------------------------------------------------------|
| patch_id       | string (UUID)  | PatchOperation ID                                    |
| job_id         | string (UUID)  | Parent Job ID                                        |
| target_path    | string         | Vault path of the affected note                      |
| operation_type | string         | Operation type (add_tag, add_backlink, etc.)         |
| payload        | dict           | Operation payload                                    |
| status         | string         | Current status (pending_approval, applied, etc.)     |
| risk_level     | string         | Risk classification (low, high)                      |
| created_at     | datetime       | When the patch was created                           |
| applied_at     | datetime/null  | When the patch was applied (if applicable)           |

### New: PatchListResponse (Pydantic schema only)

Response for the patches list endpoint.

| Field    | Type                | Description                       |
|----------|---------------------|-----------------------------------|
| patches  | list[PatchListItem] | List of patch operations          |
| total    | int                 | Total count matching the filter   |

## Relationships

- VaultStructureNode is derived from the Obsidian API folder listing (not stored in DB).
- PatchListItem maps directly to existing PatchOperation database records.
- All other data consumed by the dashboard comes from existing API response schemas.

## API Endpoint to Data Source Mapping

| Dashboard View       | API Endpoints Used                                              |
|----------------------|-----------------------------------------------------------------|
| System Dashboard     | GET /health, GET /vault-health/dashboard, GET /vault-health/trends |
| Notes Browser        | GET /vault-structure (new), GET /notes/folder/{path}, GET /notes/{path} |
| Patches & Approvals  | GET /patches (new), POST /patches/{id}/approve, POST /patches/{id}/reject |
| Jobs Monitor         | GET /jobs, GET /jobs/{id}, POST /jobs/{id}/cancel, POST /jobs   |
| AI Chat              | POST /ai/chat                                                   |
| Audit Logs           | GET /logs                                                       |
