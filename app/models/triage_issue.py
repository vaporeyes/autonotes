# ABOUTME: SQLAlchemy model for TriageIssue representing a detected convention violation.
# ABOUTME: Tracks issue type, risk level, resolution status, and rejection suppression.

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class IssueType(str, enum.Enum):
    missing_frontmatter = "missing_frontmatter"
    missing_tag = "missing_tag"
    missing_backlink = "missing_backlink"
    tag_normalization = "tag_normalization"


class TriageResolution(str, enum.Enum):
    auto_applied = "auto_applied"
    pending_approval = "pending_approval"
    rejected = "rejected"
    superseded = "superseded"


class TriageIssue(Base):
    __tablename__ = "triage_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    convention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("folder_conventions.id"), nullable=False
    )
    note_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    issue_type: Mapped[IssueType] = mapped_column(
        Enum(IssueType, name="issue_type_enum"), nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        Enum("low", "high", name="risk_level_enum", create_type=False), nullable=False
    )
    suggested_fix: Mapped[dict] = mapped_column(JSON, nullable=False)
    resolution: Mapped[TriageResolution] = mapped_column(
        Enum(TriageResolution, name="triage_resolution_enum"), nullable=False
    )
    patch_operation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patch_operations.id")
    )
    rejected_hash: Mapped[str | None] = mapped_column(String(64))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    job = relationship("Job", backref="triage_issues")
    convention = relationship("FolderConvention")
    patch_operation = relationship("PatchOperation")

    __table_args__ = (
        Index("ix_triage_issue_job_id", "job_id"),
        Index("ix_triage_issue_note_path_type", "note_path", "issue_type"),
        Index("ix_triage_issue_rejected_hash", "rejected_hash"),
    )
