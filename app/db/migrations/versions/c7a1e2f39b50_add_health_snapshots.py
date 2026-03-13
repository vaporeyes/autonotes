# ABOUTME: Migration adding vault_health_scan job type and health_snapshots table.
# ABOUTME: Uses raw SQL to match existing migration pattern and avoid enum auto-creation.

"""add health snapshots

Revision ID: c7a1e2f39b50
Revises: 4ac978430f84
Create Date: 2026-03-12 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a1e2f39b50"
down_revision: Union[str, None] = "4ac978430f84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'vault_health_scan'")

    op.execute("""
        CREATE TABLE health_snapshots (
            id UUID PRIMARY KEY,
            job_id UUID NOT NULL UNIQUE REFERENCES jobs(id),
            scan_scope VARCHAR(1024) NOT NULL,
            total_notes INTEGER NOT NULL,
            orphan_count INTEGER NOT NULL,
            orphan_paths JSONB NOT NULL DEFAULT '[]',
            zero_outbound_paths JSONB NOT NULL DEFAULT '[]',
            tag_distribution JSONB NOT NULL DEFAULT '{}',
            unique_tag_count INTEGER NOT NULL,
            backlink_density FLOAT NOT NULL,
            cluster_count INTEGER NOT NULL,
            cluster_sizes JSONB NOT NULL DEFAULT '[]',
            health_score FLOAT NOT NULL,
            skipped_notes JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute(
        "CREATE INDEX ix_health_snapshots_scope_created "
        "ON health_snapshots (scan_scope, created_at)"
    )
    op.execute(
        "CREATE INDEX ix_health_snapshots_created_at "
        "ON health_snapshots (created_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS health_snapshots")
    # Cannot remove enum value in PostgreSQL; left as-is
