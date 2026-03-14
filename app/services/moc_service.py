# ABOUTME: Service for generating Map of Content (MOC) drafts from note clusters.
# ABOUTME: Creates Markdown with wiki-links to cluster members, stored as PatchOperation for approval.

import hashlib
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.note_cluster import NoteCluster
from app.models.patch_operation import OperationType, PatchOperation, PatchStatus, RiskLevel
from app.schemas.cluster import MOCDraftResponse

logger = logging.getLogger(__name__)


def _generate_moc_markdown(cluster: NoteCluster, title: str) -> str:
    """Generate Markdown content for a Map of Content note."""
    lines = [f"# {title}", ""]

    lines.append(f"A curated map linking {cluster.note_count} related notes.")
    lines.append("")

    # Group members by folder prefix
    groups: dict[str, list] = {}
    for member in sorted(cluster.members, key=lambda m: m.similarity_to_centroid, reverse=True):
        parts = member.note_path.split("/")
        folder = parts[0] if len(parts) > 1 else "Root"
        if folder not in groups:
            groups[folder] = []
        # Strip .md extension for wiki-link display
        display = member.note_path.rsplit("/", 1)[-1].removesuffix(".md")
        groups[folder].append((member.note_path, display))

    if len(groups) == 1:
        # Single folder -- flat list
        for _path, display in list(groups.values())[0]:
            lines.append(f"- [[{display}]]")
    else:
        # Multiple folders -- group by heading
        for folder, members in groups.items():
            lines.append(f"## {folder}")
            lines.append("")
            for _path, display in members:
                lines.append(f"- [[{display}]]")
            lines.append("")

    lines.append("")
    return "\n".join(lines)


def _compute_idempotency_key(target_path: str, payload: dict) -> str:
    data = json.dumps({"path": target_path, "type": "create_moc", "payload": payload}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:64]


async def generate_moc(
    session: AsyncSession,
    cluster: NoteCluster,
    target_folder: str | None = None,
    title_override: str | None = None,
) -> MOCDraftResponse:
    """Generate a MOC draft from a cluster and store it as a PatchOperation."""
    folder = target_folder or settings.moc_target_folder
    if not folder.endswith("/"):
        folder += "/"

    title = title_override or f"MOC - {cluster.label}"
    filename = title.replace(" ", "-").replace("/", "-") + ".md"
    target_path = f"{folder}{filename}"

    content = _generate_moc_markdown(cluster, title)

    payload = {
        "content": content,
        "cluster_id": str(cluster.id),
        "note_count": cluster.note_count,
    }

    idempotency_key = _compute_idempotency_key(target_path, payload)

    patch = PatchOperation(
        job_id=cluster.job_id,
        target_path=target_path,
        operation_type=OperationType.create_moc,
        payload=payload,
        idempotency_key=idempotency_key,
        risk_level=RiskLevel.high,
        status=PatchStatus.pending_approval,
    )
    session.add(patch)
    await session.flush()

    return MOCDraftResponse(
        patch_id=str(patch.id),
        target_path=target_path,
        preview=content,
        note_count=cluster.note_count,
        status="pending_approval",
    )
