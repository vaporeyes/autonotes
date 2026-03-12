# ABOUTME: Initial database schema migration creating all 4 core tables.
# ABOUTME: Jobs, PatchOperations, OperationLogs, LLMInteractions with indexes.

"""initial schema

Revision ID: b51d378912c0
Revises:
Create Date: 2026-03-12 04:46:45.603274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b51d378912c0"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

job_type_enum = sa.Enum(
    "vault_scan", "vault_cleanup", "ai_analysis", "ai_chat", "manual_patch", "batch_patch",
    name="job_type_enum",
)
job_status_enum = sa.Enum("pending", "running", "completed", "failed", "cancelled", name="job_status_enum")
operation_type_enum = sa.Enum(
    "add_tag", "remove_tag", "add_backlink", "remove_backlink",
    "update_frontmatter_key", "append_body", "prepend_body",
    name="operation_type_enum",
)
risk_level_enum = sa.Enum("low", "high", name="risk_level_enum")
patch_status_enum = sa.Enum(
    "pending_approval", "approved", "applied", "skipped", "failed", name="patch_status_enum"
)
log_status_enum = sa.Enum("success", "failure", "no_op", name="log_status_enum")


def upgrade() -> None:
    job_type_enum.create(op.get_bind(), checkfirst=True)
    job_status_enum.create(op.get_bind(), checkfirst=True)
    operation_type_enum.create(op.get_bind(), checkfirst=True)
    risk_level_enum.create(op.get_bind(), checkfirst=True)
    patch_status_enum.create(op.get_bind(), checkfirst=True)
    log_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("celery_task_id", sa.String(255)),
        sa.Column("job_type", job_type_enum, nullable=False),
        sa.Column("target_path", sa.String(1024)),
        sa.Column("parameters", postgresql.JSON),
        sa.Column("idempotency_key", sa.String(64)),
        sa.Column("status", job_status_enum, nullable=False, server_default="pending"),
        sa.Column("progress_current", sa.Integer),
        sa.Column("progress_total", sa.Integer),
        sa.Column("result", postgresql.JSON),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_job_status", "jobs", ["status"])
    op.create_index("ix_job_created_at", "jobs", ["created_at"])
    op.create_index(
        "ix_job_idempotency_active",
        "jobs",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )

    op.create_table(
        "patch_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("target_path", sa.String(1024), nullable=False),
        sa.Column("operation_type", operation_type_enum, nullable=False),
        sa.Column("payload", postgresql.JSON, nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("risk_level", risk_level_enum, nullable=False),
        sa.Column("status", patch_status_enum, nullable=False, server_default="pending_approval"),
        sa.Column("before_hash", sa.String(71)),
        sa.Column("after_hash", sa.String(71)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_patch_idempotency", "patch_operations", ["idempotency_key"], unique=True)

    op.create_table(
        "operation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id")),
        sa.Column(
            "patch_operation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patch_operations.id")
        ),
        sa.Column("operation_name", sa.String(255), nullable=False),
        sa.Column("target_path", sa.String(1024), nullable=False),
        sa.Column("before_hash", sa.String(71)),
        sa.Column("after_hash", sa.String(71)),
        sa.Column("status", log_status_enum, nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("llm_notes_sent", postgresql.ARRAY(sa.String)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_oplog_target_path", "operation_logs", ["target_path"])
    op.create_index("ix_oplog_created_at", "operation_logs", ["created_at"])

    op.create_table(
        "llm_interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("notes_sent", postgresql.ARRAY(sa.String)),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_llm_job_id", "llm_interactions", ["job_id"])


def downgrade() -> None:
    op.drop_table("llm_interactions")
    op.drop_table("operation_logs")
    op.drop_table("patch_operations")
    op.drop_table("jobs")

    log_status_enum.drop(op.get_bind(), checkfirst=True)
    patch_status_enum.drop(op.get_bind(), checkfirst=True)
    risk_level_enum.drop(op.get_bind(), checkfirst=True)
    operation_type_enum.drop(op.get_bind(), checkfirst=True)
    job_status_enum.drop(op.get_bind(), checkfirst=True)
    job_type_enum.drop(op.get_bind(), checkfirst=True)
