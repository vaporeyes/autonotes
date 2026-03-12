# ABOUTME: SQLAlchemy model for OperationLog, an immutable audit record for vault mutations.
# ABOUTME: Tracks before/after content hashes, LLM note paths sent, and operation status.

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class LogStatus(str, enum.Enum):
    success = "success"
    failure = "failure"
    no_op = "no_op"


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    patch_operation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patch_operations.id")
    )
    operation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    before_hash: Mapped[str | None] = mapped_column(String(71))
    after_hash: Mapped[str | None] = mapped_column(String(71))
    status: Mapped[LogStatus] = mapped_column(Enum(LogStatus, name="log_status_enum"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    llm_notes_sent: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    job = relationship("Job", back_populates="operation_logs")
    patch_operation = relationship("PatchOperation", back_populates="operation_log")

    __table_args__ = (
        Index("ix_oplog_target_path", "target_path"),
        Index("ix_oplog_created_at", "created_at"),
    )
