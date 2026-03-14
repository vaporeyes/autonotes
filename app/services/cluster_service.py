# ABOUTME: Service for HDBSCAN clustering of note embeddings and duplicate detection.
# ABOUTME: Groups notes into topic clusters, assigns labels, and finds near-duplicate pairs.

import logging
from collections import Counter

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.duplicate_pair import DuplicatePair
from app.models.note_cluster import ClusterMember, NoteCluster
from app.models.note_embedding import NoteEmbedding

logger = logging.getLogger(__name__)


def _label_from_paths(paths: list[str]) -> str:
    """Generate a cluster label from the most common folder prefix among member paths."""
    folders = []
    for p in paths:
        parts = p.split("/")
        if len(parts) >= 2:
            folders.append(parts[0] + "/" + parts[1] if len(parts) > 2 else parts[0])
        else:
            folders.append(parts[0])
    if not folders:
        return "Miscellaneous"
    counter = Counter(folders)
    most_common = counter.most_common(1)[0][0]
    return most_common.replace("/", " - ")


async def run_clustering(
    session: AsyncSession,
    job_id: str,
    min_cluster_size: int | None = None,
    duplicate_threshold: float | None = None,
    progress_callback=None,
) -> dict:
    """Run HDBSCAN clustering and duplicate detection on all stored embeddings."""
    if min_cluster_size is None:
        min_cluster_size = settings.cluster_min_size
    if duplicate_threshold is None:
        duplicate_threshold = settings.duplicate_default_threshold

    # Load all embeddings
    result = await session.execute(select(NoteEmbedding))
    embeddings = list(result.scalars().all())

    if len(embeddings) < 2:
        return {
            "clusters_created": 0,
            "unclustered_count": len(embeddings),
            "duplicates_found": 0,
            "total_notes": len(embeddings),
        }

    paths = [e.note_path for e in embeddings]
    vectors = np.array([e.embedding for e in embeddings], dtype=np.float32)

    if progress_callback:
        await progress_callback(1, 4)

    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normalized = vectors / norms

    # Duplicate detection via all-pairs cosine similarity
    sim_matrix = cosine_similarity(normalized)
    duplicate_pairs = []
    n = len(paths)
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i, j] >= duplicate_threshold:
                duplicate_pairs.append((paths[i], paths[j], float(sim_matrix[i, j])))

    # Store duplicate pairs
    for path_a, path_b, score in duplicate_pairs:
        session.add(DuplicatePair(
            job_id=job_id,
            note_path_a=path_a,
            note_path_b=path_b,
            similarity_score=score,
        ))
    await session.flush()

    if progress_callback:
        await progress_callback(2, 4)

    # HDBSCAN clustering
    # Use cosine distance (1 - similarity) as the metric
    distance_matrix = 1 - sim_matrix
    np.fill_diagonal(distance_matrix, 0)

    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="precomputed",
    )
    labels = clusterer.fit_predict(distance_matrix)

    if progress_callback:
        await progress_callback(3, 4)

    # Build clusters
    cluster_map = {}
    unclustered = 0
    for idx, label in enumerate(labels):
        if label == -1:
            unclustered += 1
            continue
        if label not in cluster_map:
            cluster_map[label] = []
        cluster_map[label].append(idx)

    # Delete old clusters from this job (shouldn't exist, but safety)
    # Create new cluster records
    clusters_created = 0
    for label_id, member_indices in cluster_map.items():
        member_paths = [paths[i] for i in member_indices]
        cluster_label = _label_from_paths(member_paths)

        # Compute centroid
        cluster_vectors = normalized[member_indices]
        centroid = cluster_vectors.mean(axis=0)
        centroid_norm = np.linalg.norm(centroid)
        if centroid_norm > 0:
            centroid = centroid / centroid_norm

        cluster = NoteCluster(
            job_id=job_id,
            label=cluster_label,
            note_count=len(member_indices),
        )
        session.add(cluster)
        await session.flush()

        for idx in member_indices:
            sim_to_centroid = float(np.dot(normalized[idx], centroid))
            session.add(ClusterMember(
                cluster_id=cluster.id,
                note_path=paths[idx],
                similarity_to_centroid=round(sim_to_centroid, 4),
            ))

        clusters_created += 1

    await session.flush()

    if progress_callback:
        await progress_callback(4, 4)

    return {
        "clusters_created": clusters_created,
        "unclustered_count": unclustered,
        "duplicates_found": len(duplicate_pairs),
        "total_notes": len(embeddings),
    }
