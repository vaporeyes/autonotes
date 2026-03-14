# ABOUTME: SQLAlchemy model for DuplicatePair storing detected near-duplicate note pairs.
# ABOUTME: Pairs are produced by batch cosine similarity scans during clustering jobs.

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DuplicatePair(Base):
    __tablename__ = "duplicate_pairs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    note_path_a: Mapped[str] = mapped_column(String(1024), nullable=False)
    note_path_b: Mapped[str] = mapped_column(String(1024), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_duplicate_pair_job_id", "job_id"),
        UniqueConstraint("job_id", "note_path_a", "note_path_b", name="uq_duplicate_pair_per_job"),
    )
