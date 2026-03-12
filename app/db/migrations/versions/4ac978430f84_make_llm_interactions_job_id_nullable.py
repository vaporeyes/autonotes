# ABOUTME: Migration to make llm_interactions.job_id nullable for chat interactions.
# ABOUTME: Chat requests have no associated job, so job_id must allow NULL.

"""make llm_interactions job_id nullable

Revision ID: 4ac978430f84
Revises: b51d378912c0
Create Date: 2026-03-12 11:34:51.685196

"""
from typing import Sequence, Union

from alembic import op


revision: str = "4ac978430f84"
down_revision: Union[str, Sequence[str], None] = "b51d378912c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE llm_interactions ALTER COLUMN job_id DROP NOT NULL")


def downgrade() -> None:
    op.execute("DELETE FROM llm_interactions WHERE job_id IS NULL")
    op.execute("ALTER TABLE llm_interactions ALTER COLUMN job_id SET NOT NULL")
