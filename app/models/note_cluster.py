# ABOUTME: SQLAlchemy models for NoteCluster and ClusterMember representing topic groupings.
# ABOUTME: Clusters are produced by HDBSCAN clustering jobs over note embeddings.

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class NoteCluster(Base):
    __tablename__ = "note_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    note_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    members = relationship("ClusterMember", back_populates="cluster", lazy="selectin", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_note_cluster_job_id", "job_id"),
    )


class ClusterMember(Base):
    __tablename__ = "cluster_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("note_clusters.id", ondelete="CASCADE"), nullable=False
    )
    note_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    similarity_to_centroid: Mapped[float] = mapped_column(Float, nullable=False)

    cluster = relationship("NoteCluster", back_populates="members")

    __table_args__ = (
        Index("ix_cluster_member_cluster_id", "cluster_id"),
        Index("ix_cluster_member_note_path", "note_path"),
    )
