# ABOUTME: Routes for similarity search, duplicate detection results, and embedding status.
# ABOUTME: POST /similarity/search, GET /similarity/duplicates/{job_id}, GET /embeddings/status.

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import not_found, validation_error
from app.db.session import get_session
from app.models.duplicate_pair import DuplicatePair
from app.models.job import Job, JobType
from app.schemas.similarity import (
    DuplicatePairResponse,
    DuplicatesResponse,
    EmbeddingStatusResponse,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from app.services import embedding_service, similarity_service
from app.services.obsidian_client import ObsidianClient

router = APIRouter()


@router.post("/similarity/search", response_model=SimilaritySearchResponse, tags=["Similarity"])
async def search_similar(req: SimilaritySearchRequest, session: AsyncSession = Depends(get_session)):
    if not req.note_path and not req.query:
        raise validation_error("Either note_path or query must be provided")
    if req.note_path and req.query:
        raise validation_error("Provide either note_path or query, not both")

    result = await similarity_service.search_similar(
        session=session,
        note_path=req.note_path,
        query=req.query,
        threshold=req.threshold,
        limit=req.limit,
    )
    return result


@router.get("/similarity/duplicates/{job_id}", response_model=DuplicatesResponse, tags=["Similarity"])
async def get_duplicates(
    job_id: uuid.UUID,
    threshold: float = Query(default=0.9, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    job = await session.get(Job, job_id)
    if not job or job.job_type != JobType.cluster_notes:
        raise not_found(f"No clustering results found for job {job_id}")

    result = await session.execute(
        select(DuplicatePair)
        .where(DuplicatePair.job_id == job_id, DuplicatePair.similarity_score >= threshold)
        .order_by(DuplicatePair.similarity_score.desc())
        .limit(limit)
    )
    pairs = list(result.scalars().all())

    return DuplicatesResponse(
        job_id=str(job_id),
        threshold=threshold,
        pairs=[
            DuplicatePairResponse(
                note_path_a=p.note_path_a,
                note_path_b=p.note_path_b,
                similarity=p.similarity_score,
            )
            for p in pairs
        ],
        total=len(pairs),
    )


@router.get("/embeddings/status", response_model=EmbeddingStatusResponse, tags=["Embeddings"])
async def get_embedding_status(session: AsyncSession = Depends(get_session)):
    client = ObsidianClient()
    try:
        all_files = await client.list_folder("", recursive=True)
        total_vault_notes = len([f for f in all_files if f.endswith(".md")])
    except Exception:
        total_vault_notes = 0
    finally:
        await client.close()

    status = await embedding_service.get_embedding_status(session, total_vault_notes)

    # Find latest embedding job
    result = await session.execute(
        select(Job)
        .where(Job.job_type == JobType.embed_notes)
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    latest_job = result.scalar_one_or_none()

    return EmbeddingStatusResponse(
        total_embedded=status["total_embedded"],
        total_vault_notes=status["total_vault_notes"],
        stale_count=status["stale_count"],
        last_job_id=str(latest_job.id) if latest_job else None,
        last_embedded_at=status["last_embedded_at"],
        model=status["model"],
        coverage_percent=status["coverage_percent"],
    )
