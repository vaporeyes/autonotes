# ABOUTME: SQLAlchemy model for the Job entity representing a trackable unit of work.
# ABOUTME: Supports vault_scan, vault_cleanup, ai_analysis, ai_chat, manual_patch, batch_patch, vault_health_scan, triage_scan.

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class JobType(str, enum.Enum):
    vault_scan = "vault_scan"
    vault_cleanup = "vault_cleanup"
    ai_analysis = "ai_analysis"
    ai_chat = "ai_chat"
    manual_patch = "manual_patch"
    batch_patch = "batch_patch"
    vault_health_scan = "vault_health_scan"
    triage_scan = "triage_scan"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    job_type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type_enum"), nullable=False)
    target_path: Mapped[str | None] = mapped_column(String(1024))
    parameters: Mapped[dict | None] = mapped_column(JSON)
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"), nullable=False, default=JobStatus.pending
    )
    progress_current: Mapped[int | None] = mapped_column(Integer)
    progress_total: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patch_operations = relationship("PatchOperation", back_populates="job", lazy="selectin")
    operation_logs = relationship("OperationLog", back_populates="job", lazy="selectin")
    llm_interactions = relationship("LLMInteraction", back_populates="job", lazy="selectin")

    __table_args__ = (
        Index(
            "ix_job_idempotency_active",
            "idempotency_key",
            unique=True,
            postgresql_where=(status.in_([JobStatus.pending, JobStatus.running])),
        ),
        Index("ix_job_status", "status"),
        Index("ix_job_created_at", "created_at"),
    )
