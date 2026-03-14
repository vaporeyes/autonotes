# ABOUTME: SQLAlchemy model for NoteEmbedding storing vector embeddings for vault notes.
# ABOUTME: Uses pgvector VECTOR(1536) column for OpenAI text-embedding-3-small vectors.

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class NoteEmbedding(Base):
    __tablename__ = "note_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding = mapped_column(Vector(1536), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="text-embedding-3-small")
    embedded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_note_embedding_path", "note_path", unique=True),
        Index("ix_note_embedding_hash", "content_hash"),
    )
