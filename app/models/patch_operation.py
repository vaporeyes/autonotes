# ABOUTME: SQLAlchemy model for PatchOperation representing a targeted note modification.
# ABOUTME: Tracks operation type, risk level, idempotency key, and before/after content hashes.

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OperationType(str, enum.Enum):
    add_tag = "add_tag"
    remove_tag = "remove_tag"
    add_backlink = "add_backlink"
    remove_backlink = "remove_backlink"
    update_frontmatter_key = "update_frontmatter_key"
    append_body = "append_body"
    prepend_body = "prepend_body"
    create_moc = "create_moc"


class RiskLevel(str, enum.Enum):
    low = "low"
    high = "high"


class PatchStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    applied = "applied"
    skipped = "skipped"
    failed = "failed"


class PatchOperation(Base):
    __tablename__ = "patch_operations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    target_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    operation_type: Mapped[OperationType] = mapped_column(
        Enum(OperationType, name="operation_type_enum"), nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel, name="risk_level_enum"), nullable=False)
    status: Mapped[PatchStatus] = mapped_column(
        Enum(PatchStatus, name="patch_status_enum"), nullable=False, default=PatchStatus.pending_approval
    )
    before_hash: Mapped[str | None] = mapped_column(String(71))
    after_hash: Mapped[str | None] = mapped_column(String(71))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job = relationship("Job", back_populates="patch_operations")
    operation_log = relationship("OperationLog", back_populates="patch_operation", uselist=False)

    __table_args__ = (
        Index("ix_patch_idempotency", "idempotency_key", unique=True),
    )
