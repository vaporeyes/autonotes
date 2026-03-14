# ABOUTME: Service for generating and storing OpenAI vector embeddings for vault notes.
# ABOUTME: Supports batch embedding, incremental updates via content hash, and on-the-fly embedding.

import hashlib
import logging
from datetime import datetime, timezone

import frontmatter
import openai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.note_embedding import NoteEmbedding

logger = logging.getLogger(__name__)


def _body_hash(raw_content: str) -> str:
    """Hash the note body (excluding frontmatter) for staleness detection."""
    body = _body_text(raw_content)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _body_text(raw_content: str) -> str:
    """Extract the body text from a note, excluding frontmatter YAML."""
    try:
        post = frontmatter.loads(raw_content)
        return post.content.strip()
    except Exception:
        # Malformed frontmatter -- fall back to raw content
        return raw_content.strip()


# text-embedding-3-small has an 8192 token limit; ~4 chars per token is a safe estimate
_MAX_CHARS = 8192 * 3


def _truncate(text: str) -> str:
    """Truncate text to stay within the embedding model's token limit."""
    if len(text) <= _MAX_CHARS:
        return text
    return text[:_MAX_CHARS]


def _get_openai_client() -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_embeddings(texts: list[str]) -> list[dict]:
    """Call OpenAI embeddings API for a batch of texts. Returns list of {embedding, token_count}."""
    if not texts:
        return []
    client = _get_openai_client()
    truncated = [_truncate(t) for t in texts]
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=truncated,
        dimensions=settings.embedding_dimensions,
    )
    results = []
    for item in response.data:
        results.append({
            "embedding": item.embedding,
            "token_count": response.usage.total_tokens // len(texts),
        })
    return results


async def embed_single_text(text: str) -> dict:
    """Embed a single text string. Returns {embedding, token_count}."""
    results = await generate_embeddings([text])
    return results[0]


async def embed_note(
    session: AsyncSession,
    note_path: str,
    raw_content: str,
) -> NoteEmbedding | None:
    """Embed a single note and store/update the embedding. Returns the NoteEmbedding or None if skipped."""
    body = _body_text(raw_content)
    if not body:
        return None

    content_hash = _body_hash(raw_content)

    # Check if embedding already exists and is current
    result = await session.execute(
        select(NoteEmbedding).where(NoteEmbedding.note_path == note_path)
    )
    existing = result.scalar_one_or_none()
    if existing and existing.content_hash == content_hash:
        return existing

    embed_result = await embed_single_text(body)
    now = datetime.now(timezone.utc)

    if existing:
        existing.content_hash = content_hash
        existing.embedding = embed_result["embedding"]
        existing.token_count = embed_result["token_count"]
        existing.model = settings.embedding_model
        existing.embedded_at = now
        return existing
    else:
        embedding = NoteEmbedding(
            note_path=note_path,
            content_hash=content_hash,
            embedding=embed_result["embedding"],
            token_count=embed_result["token_count"],
            model=settings.embedding_model,
            embedded_at=now,
            created_at=now,
        )
        session.add(embedding)
        return embedding


async def embed_notes_batch(
    session: AsyncSession,
    notes: list[tuple[str, str]],
    progress_callback=None,
) -> dict:
    """Embed a batch of notes (path, raw_content). Returns stats dict."""
    embedded = 0
    skipped = 0
    total = len(notes)

    # Build list of notes that need embedding
    to_embed = []
    for note_path, raw_content in notes:
        try:
            body = _body_text(raw_content)
            if not body:
                skipped += 1
                if progress_callback:
                    await progress_callback(embedded + skipped, total)
                continue
            content_hash = _body_hash(raw_content)
            result = await session.execute(
                select(NoteEmbedding).where(NoteEmbedding.note_path == note_path)
            )
            existing = result.scalar_one_or_none()
            if existing and existing.content_hash == content_hash:
                skipped += 1
                if progress_callback:
                    await progress_callback(embedded + skipped, total)
                continue
            to_embed.append((note_path, raw_content, body, content_hash, existing))
        except Exception:
            logger.warning("Failed to process note for embedding: %s", note_path)
            skipped += 1

    # Process in batches
    batch_size = settings.embedding_batch_size
    for i in range(0, len(to_embed), batch_size):
        batch = to_embed[i : i + batch_size]
        texts = [item[2] for item in batch]  # body texts

        try:
            embed_results = await generate_embeddings(texts)
        except Exception:
            logger.exception("Batch %d failed, falling back to individual embedding", i // batch_size)
            # Fall back to one-at-a-time for this batch
            for note_path, _raw, body, content_hash, existing in batch:
                try:
                    single_result = await generate_embeddings([body])
                    embed_result = single_result[0]
                    now = datetime.now(timezone.utc)
                    if existing:
                        existing.content_hash = content_hash
                        existing.embedding = embed_result["embedding"]
                        existing.token_count = embed_result["token_count"]
                        existing.model = settings.embedding_model
                        existing.embedded_at = now
                    else:
                        session.add(NoteEmbedding(
                            note_path=note_path,
                            content_hash=content_hash,
                            embedding=embed_result["embedding"],
                            token_count=embed_result["token_count"],
                            model=settings.embedding_model,
                            embedded_at=now,
                            created_at=now,
                        ))
                    embedded += 1
                except Exception:
                    logger.warning("Skipping note that failed to embed: %s", note_path)
                    skipped += 1
                if progress_callback:
                    await progress_callback(embedded + skipped, total)
            await session.flush()
            continue

        now = datetime.now(timezone.utc)
        for (note_path, _raw, _body, content_hash, existing), embed_result in zip(batch, embed_results):
            if existing:
                existing.content_hash = content_hash
                existing.embedding = embed_result["embedding"]
                existing.token_count = embed_result["token_count"]
                existing.model = settings.embedding_model
                existing.embedded_at = now
            else:
                session.add(NoteEmbedding(
                    note_path=note_path,
                    content_hash=content_hash,
                    embedding=embed_result["embedding"],
                    token_count=embed_result["token_count"],
                    model=settings.embedding_model,
                    embedded_at=now,
                    created_at=now,
                ))
            embedded += 1
            if progress_callback:
                await progress_callback(embedded + skipped, total)

        await session.flush()

    return {"notes_embedded": embedded, "notes_skipped": skipped, "notes_total": total}


async def get_embedding_status(session: AsyncSession, total_vault_notes: int) -> dict:
    """Get current embedding index status."""
    result = await session.execute(select(NoteEmbedding))
    embeddings = list(result.scalars().all())
    total_embedded = len(embeddings)
    last_embedded_at = max((e.embedded_at for e in embeddings), default=None) if embeddings else None

    coverage = (total_embedded / total_vault_notes * 100) if total_vault_notes > 0 else 0.0

    return {
        "total_embedded": total_embedded,
        "total_vault_notes": total_vault_notes,
        "stale_count": 0,  # Computed during scan, not stored
        "last_embedded_at": last_embedded_at,
        "model": settings.embedding_model,
        "coverage_percent": round(coverage, 1),
    }
