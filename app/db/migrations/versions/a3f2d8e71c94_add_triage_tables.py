# ABOUTME: Migration adding triage_scan job type, folder_conventions table, and triage_issues table.
# ABOUTME: Uses raw SQL to match existing migration pattern and avoid enum auto-creation.

"""add triage tables

Revision ID: a3f2d8e71c94
Revises: c7a1e2f39b50
Create Date: 2026-03-12 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f2d8e71c94"
down_revision: Union[str, None] = "c7a1e2f39b50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'triage_scan'")

    op.execute("CREATE TYPE issue_type_enum AS ENUM ("
               "'missing_frontmatter', 'missing_tag', 'missing_backlink', 'tag_normalization')")
    op.execute("CREATE TYPE triage_resolution_enum AS ENUM ("
               "'auto_applied', 'pending_approval', 'rejected', 'superseded')")

    op.execute("""
        CREATE TABLE folder_conventions (
            id UUID PRIMARY KEY,
            folder_path VARCHAR(1024) NOT NULL,
            required_frontmatter JSONB NOT NULL DEFAULT '[]',
            expected_tags JSONB NOT NULL DEFAULT '[]',
            backlink_targets JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX ix_folder_convention_path ON folder_conventions (folder_path)"
    )

    op.execute("""
        CREATE TABLE triage_issues (
            id UUID PRIMARY KEY,
            job_id UUID NOT NULL REFERENCES jobs(id),
            convention_id UUID NOT NULL REFERENCES folder_conventions(id),
            note_path VARCHAR(1024) NOT NULL,
            issue_type issue_type_enum NOT NULL,
            risk_level risk_level_enum NOT NULL,
            suggested_fix JSONB NOT NULL,
            resolution triage_resolution_enum NOT NULL,
            patch_operation_id UUID REFERENCES patch_operations(id),
            rejected_hash VARCHAR(64),
            rejected_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_triage_issue_job_id ON triage_issues (job_id)")
    op.execute(
        "CREATE INDEX ix_triage_issue_note_path_type ON triage_issues (note_path, issue_type)"
    )
    op.execute("CREATE INDEX ix_triage_issue_rejected_hash ON triage_issues (rejected_hash)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS triage_issues")
    op.execute("DROP TABLE IF EXISTS folder_conventions")
    op.execute("DROP TYPE IF EXISTS triage_resolution_enum")
    op.execute("DROP TYPE IF EXISTS issue_type_enum")
    # Cannot remove enum value in PostgreSQL; left as-is
