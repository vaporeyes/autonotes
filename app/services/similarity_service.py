# ABOUTME: Service for vector similarity search and on-the-fly embedding.
# ABOUTME: Uses pgvector cosine distance for ranked note-to-note and free-text similarity queries.

import logging

import frontmatter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note_embedding import NoteEmbedding
from app.schemas.similarity import SimilarityResultItem, SimilaritySearchResponse
from app.services import embedding_service
from app.services.obsidian_client import ObsidianClient

logger = logging.getLogger(__name__)


def _extract_title(raw_content: str, note_path: str) -> str:
    """Extract title from frontmatter or first heading, falling back to filename."""
    post = frontmatter.loads(raw_content)
    if post.metadata.get("title"):
        return post.metadata["title"]
    for line in post.content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return note_path.rsplit("/", 1)[-1].removesuffix(".md")


def _extract_tags(raw_content: str) -> list[str]:
    """Extract tags from frontmatter."""
    post = frontmatter.loads(raw_content)
    tags = post.metadata.get("tags", [])
    if isinstance(tags, str):
        return [tags]
    if isinstance(tags, list):
        return tags
    return []


async def search_similar(
    session: AsyncSession,
    note_path: str | None = None,
    query: str | None = None,
    threshold: float = 0.5,
    limit: int = 20,
) -> SimilaritySearchResponse:
    """Search for similar notes by note path or free-text query."""

    embedded_on_the_fly = False

    if note_path:
        # Get or create embedding for the source note
        from sqlalchemy import select
        result = await session.execute(
            select(NoteEmbedding).where(NoteEmbedding.note_path == note_path)
        )
        source_embedding = result.scalar_one_or_none()

        if not source_embedding:
            # On-the-fly embedding (FR-014)
            client = ObsidianClient()
            try:
                raw = await client.get_note_raw(note_path)
            finally:
                await client.close()
            source_embedding = await embedding_service.embed_note(session, note_path, raw)
            await session.flush()
            if not source_embedding:
                return SimilaritySearchResponse(
                    source=note_path, results=[], total=0, threshold=threshold
                )
            embedded_on_the_fly = True

        query_vector = source_embedding.embedding
        source_label = note_path
        exclude_path = note_path
    else:
        # Free-text query: embed the query string
        embed_result = await embedding_service.embed_single_text(query)
        query_vector = embed_result["embedding"]
        source_label = "[free-text query]"
        exclude_path = None

    # pgvector cosine distance: <=> operator returns distance (0=identical), so similarity = 1 - distance
    # Use CAST() instead of :: shorthand to avoid SQLAlchemy bind-parameter syntax conflict
    # Split into two queries to avoid asyncpg ambiguous parameter type on the IS NULL check
    vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
    if exclude_path:
        sql = text("""
            SELECT note_path, 1 - (embedding <=> CAST(:query_vec AS vector)) as similarity
            FROM note_embeddings
            WHERE note_path != :exclude_path
              AND 1 - (embedding <=> CAST(:query_vec AS vector)) >= :threshold
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :limit
        """)
        params = {
            "query_vec": vector_str,
            "exclude_path": exclude_path,
            "threshold": threshold,
            "limit": limit,
        }
    else:
        sql = text("""
            SELECT note_path, 1 - (embedding <=> CAST(:query_vec AS vector)) as similarity
            FROM note_embeddings
            WHERE 1 - (embedding <=> CAST(:query_vec AS vector)) >= :threshold
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :limit
        """)
        params = {
            "query_vec": vector_str,
            "threshold": threshold,
            "limit": limit,
        }
    result = await session.execute(sql, params)
    rows = result.fetchall()

    # Enrich results with title and tags from vault
    items = []
    client = ObsidianClient()
    try:
        for row in rows:
            path = row[0]
            sim = round(float(row[1]), 4)
            title = path.rsplit("/", 1)[-1].removesuffix(".md")
            tags = []
            try:
                raw = await client.get_note_raw(path)
                title = _extract_title(raw, path)
                tags = _extract_tags(raw)
            except Exception:
                pass
            items.append(SimilarityResultItem(
                note_path=path, similarity=sim, title=title, tags=tags
            ))
    finally:
        await client.close()

    return SimilaritySearchResponse(
        source=source_label,
        results=items,
        total=len(items),
        threshold=threshold,
        embedded_on_the_fly=embedded_on_the_fly,
    )
