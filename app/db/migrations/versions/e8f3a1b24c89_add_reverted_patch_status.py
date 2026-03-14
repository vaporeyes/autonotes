# ABOUTME: Migration adding 'reverted' value to the patch_status_enum type.
# ABOUTME: Supports undo/rollback of previously applied patch operations.

"""add reverted patch status

Revision ID: e8f3a1b24c89
Revises: d5e8f2a13b67
Create Date: 2026-03-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f3a1b24c89"
down_revision: Union[str, None] = "d5e8f2a13b67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE patch_status_enum ADD VALUE IF NOT EXISTS 'reverted'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; this is a no-op.
    pass
