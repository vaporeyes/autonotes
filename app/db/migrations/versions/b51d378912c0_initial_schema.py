# ABOUTME: Initial database schema migration creating all 4 core tables.
# ABOUTME: Jobs, PatchOperations, OperationLogs, LLMInteractions with indexes.

"""initial schema

Revision ID: b51d378912c0
Revises:
Create Date: 2026-03-12 04:46:45.603274

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b51d378912c0"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE job_type_enum AS ENUM ('vault_scan', 'vault_cleanup', 'ai_analysis', 'ai_chat', 'manual_patch', 'batch_patch')")
    op.execute("CREATE TYPE job_status_enum AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled')")
    op.execute("CREATE TYPE operation_type_enum AS ENUM ('add_tag', 'remove_tag', 'add_backlink', 'remove_backlink', 'update_frontmatter_key', 'append_body', 'prepend_body')")
    op.execute("CREATE TYPE risk_level_enum AS ENUM ('low', 'high')")
    op.execute("CREATE TYPE patch_status_enum AS ENUM ('pending_approval', 'approved', 'applied', 'skipped', 'failed')")
    op.execute("CREATE TYPE log_status_enum AS ENUM ('success', 'failure', 'no_op')")

    op.execute("""
        CREATE TABLE jobs (
            id UUID PRIMARY KEY,
            celery_task_id VARCHAR(255),
            job_type job_type_enum NOT NULL,
            target_path VARCHAR(1024),
            parameters JSONB,
            idempotency_key VARCHAR(64),
            status job_status_enum NOT NULL DEFAULT 'pending',
            progress_current INTEGER,
            progress_total INTEGER,
            result JSONB,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX ix_job_status ON jobs (status)")
    op.execute("CREATE INDEX ix_job_created_at ON jobs (created_at)")
    op.execute("CREATE UNIQUE INDEX ix_job_idempotency_active ON jobs (idempotency_key) WHERE status IN ('pending', 'running')")

    op.execute("""
        CREATE TABLE patch_operations (
            id UUID PRIMARY KEY,
            job_id UUID NOT NULL REFERENCES jobs(id),
            target_path VARCHAR(1024) NOT NULL,
            operation_type operation_type_enum NOT NULL,
            payload JSONB NOT NULL,
            idempotency_key VARCHAR(64) NOT NULL,
            risk_level risk_level_enum NOT NULL,
            status patch_status_enum NOT NULL DEFAULT 'pending_approval',
            before_hash VARCHAR(71),
            after_hash VARCHAR(71),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            applied_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE UNIQUE INDEX ix_patch_idempotency ON patch_operations (idempotency_key)")

    op.execute("""
        CREATE TABLE operation_logs (
            id UUID PRIMARY KEY,
            job_id UUID REFERENCES jobs(id),
            patch_operation_id UUID REFERENCES patch_operations(id),
            operation_name VARCHAR(255) NOT NULL,
            target_path VARCHAR(1024) NOT NULL,
            before_hash VARCHAR(71),
            after_hash VARCHAR(71),
            status log_status_enum NOT NULL,
            error_message TEXT,
            llm_notes_sent TEXT[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_oplog_target_path ON operation_logs (target_path)")
    op.execute("CREATE INDEX ix_oplog_created_at ON operation_logs (created_at)")

    op.execute("""
        CREATE TABLE llm_interactions (
            id UUID PRIMARY KEY,
            job_id UUID NOT NULL REFERENCES jobs(id),
            provider VARCHAR(50) NOT NULL,
            model VARCHAR(100) NOT NULL,
            notes_sent TEXT[],
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_llm_job_id ON llm_interactions (job_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_interactions")
    op.execute("DROP TABLE IF EXISTS operation_logs")
    op.execute("DROP TABLE IF EXISTS patch_operations")
    op.execute("DROP TABLE IF EXISTS jobs")
    op.execute("DROP TYPE IF EXISTS log_status_enum")
    op.execute("DROP TYPE IF EXISTS patch_status_enum")
    op.execute("DROP TYPE IF EXISTS risk_level_enum")
    op.execute("DROP TYPE IF EXISTS operation_type_enum")
    op.execute("DROP TYPE IF EXISTS job_status_enum")
    op.execute("DROP TYPE IF EXISTS job_type_enum")
