# ABOUTME: Routes for viewing note clusters and generating MOC drafts.
# ABOUTME: GET /clusters/latest, GET /clusters/{id}, POST /clusters/{id}/moc.

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import not_found, validation_error
from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.models.note_cluster import ClusterMember, NoteCluster
from app.schemas.cluster import (
    ClusterListResponse,
    ClusterMemberResponse,
    ClusterResponse,
    MOCDraftResponse,
    MOCGenerateRequest,
)
from app.services import moc_service

router = APIRouter(tags=["Clusters"])


@router.get("/clusters/latest", response_model=ClusterListResponse)
async def get_latest_clusters(
    min_size: int = Query(default=2, ge=1),
    session: AsyncSession = Depends(get_session),
):
    # Find the latest completed clustering job
    result = await session.execute(
        select(Job)
        .where(Job.job_type == JobType.cluster_notes, Job.status == JobStatus.completed)
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise validation_error("No clustering job has been run yet")

    result = await session.execute(
        select(NoteCluster)
        .where(NoteCluster.job_id == job.id, NoteCluster.note_count >= min_size)
        .order_by(NoteCluster.note_count.desc())
    )
    clusters = list(result.scalars().all())

    # Count unclustered (notes in embeddings but not in any cluster for this job)
    result = await session.execute(
        select(ClusterMember.note_path)
        .join(NoteCluster)
        .where(NoteCluster.job_id == job.id)
    )
    clustered_paths = {row[0] for row in result.fetchall()}

    from app.models.note_embedding import NoteEmbedding
    result = await session.execute(select(NoteEmbedding.note_path))
    all_embedded_paths = {row[0] for row in result.fetchall()}
    unclustered_count = len(all_embedded_paths - clustered_paths)

    return ClusterListResponse(
        job_id=str(job.id),
        created_at=job.created_at,
        clusters=[
            ClusterResponse(
                id=str(c.id),
                job_id=str(c.job_id),
                label=c.label,
                note_count=c.note_count,
                notes=[
                    ClusterMemberResponse(
                        note_path=m.note_path,
                        similarity_to_centroid=m.similarity_to_centroid,
                    )
                    for m in c.members
                ],
                created_at=c.created_at,
            )
            for c in clusters
        ],
        unclustered_count=unclustered_count,
        total_clusters=len(clusters),
    )


@router.get("/clusters/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    cluster = await session.get(NoteCluster, cluster_id)
    if not cluster:
        raise not_found(f"Cluster not found: {cluster_id}")

    return ClusterResponse(
        id=str(cluster.id),
        job_id=str(cluster.job_id),
        label=cluster.label,
        note_count=cluster.note_count,
        notes=[
            ClusterMemberResponse(
                note_path=m.note_path,
                similarity_to_centroid=m.similarity_to_centroid,
            )
            for m in cluster.members
        ],
        created_at=cluster.created_at,
    )


@router.post("/clusters/{cluster_id}/moc", response_model=MOCDraftResponse, status_code=201)
async def generate_moc(
    cluster_id: uuid.UUID,
    req: MOCGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    cluster = await session.get(NoteCluster, cluster_id)
    if not cluster:
        raise not_found(f"Cluster not found: {cluster_id}")
    if cluster.note_count < 2:
        raise validation_error("A MOC requires at least 2 notes in the cluster")

    result = await moc_service.generate_moc(
        session=session,
        cluster=cluster,
        target_folder=req.target_folder,
        title_override=req.title,
    )
    return result
