# ABOUTME: SQLAlchemy model for FolderConvention defining expected note structure per vault folder.
# ABOUTME: Stores required frontmatter fields, expected tags, and backlink target folders.

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class FolderConvention(Base):
    __tablename__ = "folder_conventions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folder_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    required_frontmatter: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    backlink_targets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_folder_convention_path", "folder_path", unique=True),
    )
