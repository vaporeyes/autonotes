# ABOUTME: SQLAlchemy model for the HealthSnapshot entity storing vault health metrics.
# ABOUTME: Each snapshot is an immutable point-in-time record linked to a vault_health_scan job.

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    scan_scope: Mapped[str] = mapped_column(String(1024), nullable=False)
    total_notes: Mapped[int] = mapped_column(Integer, nullable=False)
    orphan_count: Mapped[int] = mapped_column(Integer, nullable=False)
    orphan_paths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    zero_outbound_paths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tag_distribution: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    unique_tag_count: Mapped[int] = mapped_column(Integer, nullable=False)
    backlink_density: Mapped[float] = mapped_column(Float, nullable=False)
    cluster_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cluster_sizes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    health_score: Mapped[float] = mapped_column(Float, nullable=False)
    skipped_notes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_health_snapshots_scope_created", "scan_scope", "created_at"),
        Index("ix_health_snapshots_created_at", "created_at"),
    )
