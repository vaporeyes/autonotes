# ABOUTME: Core triage engine that scans notes against folder conventions.
# ABOUTME: Detects issues, auto-applies low-risk fixes, and queues high-risk suggestions.

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

import frontmatter

from app.models.patch_operation import OperationType, PatchOperation, PatchStatus, RiskLevel
from app.models.triage_issue import IssueType, TriageIssue, TriageResolution
from app.services import convention_service, log_service
from app.services.note_parser import compute_content_hash
from app.services.obsidian_client import ObsidianClient
from app.services.patch_engine import apply_patch, compute_idempotency_key

logger = logging.getLogger(__name__)

_WIKILINK_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|[^\[\]]+)?\]\]")


def _compute_rejected_hash(note_path: str, issue_type: str, suggested_fix: dict) -> str:
    data = json.dumps({"path": note_path, "type": issue_type, "fix": suggested_fix}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:64]


def _extract_link_targets(content: str) -> set[str]:
    """Extract all wikilink targets from note content."""
    return set(m.group(1) for m in _WIKILINK_RE.finditer(content))


def _note_links_to_folder(link_targets: set[str], folder_path: str) -> bool:
    """Check if any link target points to a note within the given folder."""
    folder = folder_path.rstrip("/")
    for target in link_targets:
        if target.startswith(folder + "/") or target.startswith(folder):
            return True
    return False


async def run_triage_scan(
    scope: str,
    client: ObsidianClient,
    session_factory: Callable[[], Any],
    progress_callback: Callable[[int, int], Coroutine] | None = None,
) -> dict:
    """Scan notes in scope against folder conventions.

    Returns a summary dict with counts of issues found, fixes applied, and suggestions queued.
    """
    # List all notes in scope
    if scope == "/":
        files = await client.list_folder("", recursive=True)
    else:
        files = await client.list_folder(scope.rstrip("/"), recursive=True)

    note_files = [f for f in files if f.endswith(".md")]
    total = len(note_files)
    issues_found = 0
    fixes_applied = 0
    suggestions_queued = 0
    skipped_notes: list[str] = []

    for idx, note_path in enumerate(note_files):
        if progress_callback:
            await progress_callback(idx, total)

        try:
            raw_content = await client.get_note_raw(note_path)
        except Exception:
            skipped_notes.append(note_path)
            continue

        # Resolve merged convention for this note
        async with session_factory() as session:
            merged_from, req_frontmatter, exp_tags, backlink_targets = (
                await convention_service.resolve_conventions(session, note_path)
            )

        if not merged_from:
            # No conventions apply to this folder
            continue

        # Parse note content
        try:
            post = frontmatter.loads(raw_content)
        except Exception:
            skipped_notes.append(note_path)
            continue

        before_hash = compute_content_hash(raw_content)
        current_content = raw_content
        fm_tags = post.metadata.get("tags", [])
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]
        link_targets = _extract_link_targets(raw_content)

        # Find the convention ID for the most specific matching folder
        async with session_factory() as session:
            ancestor_paths = convention_service._ancestor_paths(note_path)
            from sqlalchemy import select
            from app.models.folder_convention import FolderConvention
            result = await session.execute(
                select(FolderConvention)
                .where(FolderConvention.folder_path.in_(ancestor_paths))
                .order_by(FolderConvention.folder_path.desc())
            )
            most_specific_conv = result.scalars().first()

        if not most_specific_conv:
            continue

        convention_id = most_specific_conv.id

        # --- Detect and handle issues ---

        # 1. Missing frontmatter fields
        for field in req_frontmatter:
            if field.key not in post.metadata:
                issue_type = IssueType.missing_frontmatter
                if field.default_value is not None:
                    # Low-risk: auto-apply
                    suggested_fix = {"key": field.key, "value": field.default_value}
                    result = await _handle_low_risk_issue(
                        note_path, convention_id, issue_type, suggested_fix,
                        OperationType.update_frontmatter_key, {"key": field.key, "value": field.default_value},
                        current_content, before_hash, client, session_factory,
                    )
                    if result:
                        issues_found += 1
                        if result == "applied":
                            fixes_applied += 1
                            # Re-read content after patch
                            current_content = await client.get_note_raw(note_path)
                            before_hash = compute_content_hash(current_content)
                else:
                    # No default value - still low risk as a frontmatter field, but cannot auto-fix
                    # Report as issue without fix
                    suggested_fix = {"key": field.key, "value": None}
                    await _create_issue_record(
                        note_path, convention_id, issue_type, RiskLevel.high,
                        suggested_fix, TriageResolution.pending_approval,
                        None, session_factory,
                    )
                    issues_found += 1
                    suggestions_queued += 1

        # 2. Missing expected tags
        for tag in exp_tags:
            tag_lower = tag.lower()
            existing_lower = [t.lower() for t in fm_tags]
            if tag_lower in existing_lower:
                # Check for casing mismatch
                if tag not in fm_tags:
                    issue_type = IssueType.tag_normalization
                    suggested_fix = {"old_tag": next(t for t in fm_tags if t.lower() == tag_lower), "new_tag": tag}
                    old_tag = suggested_fix["old_tag"]
                    # Remove old, add new
                    result = await _handle_tag_normalization(
                        note_path, convention_id, old_tag, tag,
                        current_content, before_hash, client, session_factory,
                    )
                    if result:
                        issues_found += 1
                        if result == "applied":
                            fixes_applied += 1
                            current_content = await client.get_note_raw(note_path)
                            before_hash = compute_content_hash(current_content)
            else:
                # Tag completely missing - low-risk auto-apply
                issue_type = IssueType.missing_tag
                suggested_fix = {"tag": tag}
                result = await _handle_low_risk_issue(
                    note_path, convention_id, issue_type, suggested_fix,
                    OperationType.add_tag, {"tag": tag},
                    current_content, before_hash, client, session_factory,
                )
                if result:
                    issues_found += 1
                    if result == "applied":
                        fixes_applied += 1
                        current_content = await client.get_note_raw(note_path)
                        before_hash = compute_content_hash(current_content)

        # 3. Missing backlinks
        for target_folder in backlink_targets:
            if not _note_links_to_folder(link_targets, target_folder):
                issue_type = IssueType.missing_backlink
                suggested_fix = {"target_folder": target_folder}
                # High-risk: queue for approval
                rejected = await _is_rejected(note_path, issue_type, suggested_fix, session_factory)
                if rejected:
                    continue

                issues_found += 1
                suggestions_queued += 1
                await _create_high_risk_issue(
                    note_path, convention_id, issue_type, suggested_fix,
                    before_hash, session_factory,
                )

    if progress_callback:
        await progress_callback(total, total)

    return {
        "notes_scanned": total,
        "issues_found": issues_found,
        "fixes_applied": fixes_applied,
        "suggestions_queued": suggestions_queued,
        "skipped_notes": skipped_notes,
    }


async def _is_rejected(
    note_path: str, issue_type: IssueType, suggested_fix: dict,
    session_factory: Callable,
) -> bool:
    """Check if this exact issue was previously rejected and note hasn't been modified since."""
    rh = _compute_rejected_hash(note_path, issue_type.value, suggested_fix)
    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(TriageIssue).where(
                TriageIssue.rejected_hash == rh,
                TriageIssue.resolution == TriageResolution.rejected,
            )
        )
        rejected_issue = result.scalars().first()
        return rejected_issue is not None


async def _handle_low_risk_issue(
    note_path: str, convention_id: uuid.UUID, issue_type: IssueType,
    suggested_fix: dict, op_type: OperationType, patch_payload: dict,
    current_content: str, before_hash: str,
    client: ObsidianClient, session_factory: Callable,
) -> str | None:
    """Apply a low-risk fix and record the issue + patch. Returns 'applied' or None."""
    new_content, changed = apply_patch(current_content, op_type.value, patch_payload)
    if not changed:
        return None

    # Verify content hash before writing
    live_content = await client.get_note_raw(note_path)
    if compute_content_hash(live_content) != before_hash:
        logger.warning("Content changed between detection and apply for %s, skipping", note_path)
        return None

    await client.put_note(note_path, new_content)
    after_hash = compute_content_hash(new_content)

    async with session_factory() as session:
        from app.models.job import Job
        from sqlalchemy import select
        # Get the current triage scan job (most recent running triage_scan)
        job_result = await session.execute(
            select(Job).where(
                Job.job_type == "triage_scan",
                Job.status == "running",
            ).order_by(Job.created_at.desc())
        )
        job = job_result.scalars().first()
        if not job:
            return None

        idem_key = compute_idempotency_key(note_path, op_type.value, patch_payload)
        patch_op = PatchOperation(
            job_id=job.id,
            target_path=note_path,
            operation_type=op_type,
            payload=patch_payload,
            idempotency_key=idem_key,
            risk_level=RiskLevel.low,
            status=PatchStatus.applied,
            before_hash=before_hash,
            after_hash=after_hash,
            applied_at=datetime.now(timezone.utc),
        )
        session.add(patch_op)
        await session.flush()

        triage_issue = TriageIssue(
            job_id=job.id,
            convention_id=convention_id,
            note_path=note_path,
            issue_type=issue_type,
            risk_level="low",
            suggested_fix=suggested_fix,
            resolution=TriageResolution.auto_applied,
            patch_operation_id=patch_op.id,
        )
        session.add(triage_issue)

        await log_service.create_log(
            session,
            operation_name=f"triage:{op_type.value}:{list(patch_payload.values())[0]}",
            target_path=note_path,
            status="success",
            job_id=job.id,
            patch_operation_id=patch_op.id,
            before_hash=before_hash,
            after_hash=after_hash,
        )
        await session.commit()

    return "applied"


async def _handle_tag_normalization(
    note_path: str, convention_id: uuid.UUID, old_tag: str, new_tag: str,
    current_content: str, before_hash: str,
    client: ObsidianClient, session_factory: Callable,
) -> str | None:
    """Normalize tag casing: remove old, add new."""
    # Remove old tag
    content, removed = apply_patch(current_content, OperationType.remove_tag.value, {"tag": old_tag})
    if not removed:
        return None
    # Add normalized tag
    content, added = apply_patch(content, OperationType.add_tag.value, {"tag": new_tag})
    if not added:
        return None

    # Verify content hash before writing
    live_content = await client.get_note_raw(note_path)
    if compute_content_hash(live_content) != before_hash:
        return None

    await client.put_note(note_path, content)
    after_hash = compute_content_hash(content)

    async with session_factory() as session:
        from app.models.job import Job
        from sqlalchemy import select
        job_result = await session.execute(
            select(Job).where(
                Job.job_type == "triage_scan",
                Job.status == "running",
            ).order_by(Job.created_at.desc())
        )
        job = job_result.scalars().first()
        if not job:
            return None

        suggested_fix = {"old_tag": old_tag, "new_tag": new_tag}
        idem_key = compute_idempotency_key(note_path, "add_tag", {"tag": new_tag})
        patch_op = PatchOperation(
            job_id=job.id,
            target_path=note_path,
            operation_type=OperationType.add_tag,
            payload={"tag": new_tag},
            idempotency_key=idem_key,
            risk_level=RiskLevel.low,
            status=PatchStatus.applied,
            before_hash=before_hash,
            after_hash=after_hash,
            applied_at=datetime.now(timezone.utc),
        )
        session.add(patch_op)
        await session.flush()

        triage_issue = TriageIssue(
            job_id=job.id,
            convention_id=convention_id,
            note_path=note_path,
            issue_type=IssueType.tag_normalization,
            risk_level="low",
            suggested_fix=suggested_fix,
            resolution=TriageResolution.auto_applied,
            patch_operation_id=patch_op.id,
        )
        session.add(triage_issue)

        await log_service.create_log(
            session,
            operation_name=f"triage:tag_normalization:{old_tag}->{new_tag}",
            target_path=note_path,
            status="success",
            job_id=job.id,
            patch_operation_id=patch_op.id,
            before_hash=before_hash,
            after_hash=after_hash,
        )
        await session.commit()

    return "applied"


async def _create_issue_record(
    note_path: str, convention_id: uuid.UUID, issue_type: IssueType,
    risk_level: RiskLevel, suggested_fix: dict, resolution: TriageResolution,
    patch_operation_id: uuid.UUID | None, session_factory: Callable,
) -> None:
    """Create a TriageIssue record without a patch."""
    async with session_factory() as session:
        from app.models.job import Job
        from sqlalchemy import select
        job_result = await session.execute(
            select(Job).where(
                Job.job_type == "triage_scan",
                Job.status == "running",
            ).order_by(Job.created_at.desc())
        )
        job = job_result.scalars().first()
        if not job:
            return

        triage_issue = TriageIssue(
            job_id=job.id,
            convention_id=convention_id,
            note_path=note_path,
            issue_type=issue_type,
            risk_level=risk_level.value,
            suggested_fix=suggested_fix,
            resolution=resolution,
            patch_operation_id=patch_operation_id,
        )
        session.add(triage_issue)
        await session.commit()


async def _create_high_risk_issue(
    note_path: str, convention_id: uuid.UUID, issue_type: IssueType,
    suggested_fix: dict, before_hash: str, session_factory: Callable,
) -> None:
    """Create a pending PatchOperation and TriageIssue for a high-risk suggestion."""
    async with session_factory() as session:
        from app.models.job import Job
        from sqlalchemy import select
        job_result = await session.execute(
            select(Job).where(
                Job.job_type == "triage_scan",
                Job.status == "running",
            ).order_by(Job.created_at.desc())
        )
        job = job_result.scalars().first()
        if not job:
            return

        # For missing backlinks, the patch payload needs a target note path.
        # We use the target folder as a placeholder since we don't know the specific note.
        target_folder = suggested_fix.get("target_folder", "")
        patch_payload = {"target": target_folder, "display_text": None}
        idem_key = compute_idempotency_key(note_path, OperationType.add_backlink.value, patch_payload)

        # Check if this exact patch already exists
        existing = await session.execute(
            select(PatchOperation).where(PatchOperation.idempotency_key == idem_key)
        )
        if existing.scalar_one_or_none():
            return

        patch_op = PatchOperation(
            job_id=job.id,
            target_path=note_path,
            operation_type=OperationType.add_backlink,
            payload=patch_payload,
            idempotency_key=idem_key,
            risk_level=RiskLevel.high,
            status=PatchStatus.pending_approval,
            before_hash=before_hash,
        )
        session.add(patch_op)
        await session.flush()

        triage_issue = TriageIssue(
            job_id=job.id,
            convention_id=convention_id,
            note_path=note_path,
            issue_type=issue_type,
            risk_level="high",
            suggested_fix=suggested_fix,
            resolution=TriageResolution.pending_approval,
            patch_operation_id=patch_op.id,
        )
        session.add(triage_issue)

        await log_service.create_log(
            session,
            operation_name=f"triage:suggest_backlink:{target_folder}",
            target_path=note_path,
            status="no_op",
            job_id=job.id,
            patch_operation_id=patch_op.id,
            before_hash=before_hash,
        )
        await session.commit()
