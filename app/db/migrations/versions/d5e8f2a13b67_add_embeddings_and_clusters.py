# ABOUTME: Migration adding pgvector extension, note_embeddings, note_clusters, cluster_members, duplicate_pairs tables.
# ABOUTME: Also adds embed_notes and cluster_notes to job_type_enum, create_moc to operation_type_enum.

"""add embeddings and clusters

Revision ID: d5e8f2a13b67
Revises: a3f2d8e71c94
Create Date: 2026-03-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d5e8f2a13b67"
down_revision: Union[str, None] = "a3f2d8e71c94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add new job types
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'embed_notes'")
    op.execute("ALTER TYPE job_type_enum ADD VALUE IF NOT EXISTS 'cluster_notes'")

    # Add new operation type
    op.execute("ALTER TYPE operation_type_enum ADD VALUE IF NOT EXISTS 'create_moc'")

    # Create note_embeddings table using raw SQL for the vector column
    op.execute("""
        CREATE TABLE note_embeddings (
            id UUID PRIMARY KEY,
            note_path VARCHAR(1024) NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            embedding vector(1536) NOT NULL,
            token_count INTEGER NOT NULL,
            model VARCHAR(64) NOT NULL DEFAULT 'text-embedding-3-small',
            embedded_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.create_index("ix_note_embedding_path", "note_embeddings", ["note_path"], unique=True)
    op.create_index("ix_note_embedding_hash", "note_embeddings", ["content_hash"])

    # Create note_clusters table
    op.create_table(
        "note_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("label", sa.String(256), nullable=False),
        sa.Column("note_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_note_cluster_job_id", "note_clusters", ["job_id"])

    # Create cluster_members table
    op.create_table(
        "cluster_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("note_clusters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note_path", sa.String(1024), nullable=False),
        sa.Column("similarity_to_centroid", sa.Float(), nullable=False),
    )
    op.create_index("ix_cluster_member_cluster_id", "cluster_members", ["cluster_id"])
    op.create_index("ix_cluster_member_note_path", "cluster_members", ["note_path"])

    # Create duplicate_pairs table
    op.create_table(
        "duplicate_pairs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("note_path_a", sa.String(1024), nullable=False),
        sa.Column("note_path_b", sa.String(1024), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "note_path_a", "note_path_b", name="uq_duplicate_pair_per_job"),
    )
    op.create_index("ix_duplicate_pair_job_id", "duplicate_pairs", ["job_id"])


def downgrade() -> None:
    op.drop_table("duplicate_pairs")
    op.drop_table("cluster_members")
    op.drop_table("note_clusters")
    op.drop_table("note_embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
