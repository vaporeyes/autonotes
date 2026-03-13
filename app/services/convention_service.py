# ABOUTME: Service layer for folder convention CRUD and inheritance resolution.
# ABOUTME: Resolves merged conventions by prefix-matching folder paths from root to leaf.

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder_convention import FolderConvention
from app.schemas.convention import FrontmatterField


async def create_convention(
    session: AsyncSession,
    folder_path: str,
    required_frontmatter: list[dict],
    expected_tags: list[str],
    backlink_targets: list[str],
) -> FolderConvention:
    convention = FolderConvention(
        folder_path=folder_path,
        required_frontmatter=required_frontmatter,
        expected_tags=expected_tags,
        backlink_targets=backlink_targets,
    )
    session.add(convention)
    await session.flush()
    return convention


async def get_convention(session: AsyncSession, convention_id: uuid.UUID) -> FolderConvention | None:
    return await session.get(FolderConvention, convention_id)


async def list_conventions(session: AsyncSession) -> list[FolderConvention]:
    result = await session.execute(select(FolderConvention).order_by(FolderConvention.folder_path))
    return list(result.scalars().all())


async def update_convention(
    session: AsyncSession,
    convention: FolderConvention,
    folder_path: str,
    required_frontmatter: list[dict],
    expected_tags: list[str],
    backlink_targets: list[str],
) -> FolderConvention:
    convention.folder_path = folder_path
    convention.required_frontmatter = required_frontmatter
    convention.expected_tags = expected_tags
    convention.backlink_targets = backlink_targets
    convention.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return convention


async def delete_convention(session: AsyncSession, convention: FolderConvention) -> None:
    await session.delete(convention)
    await session.flush()


async def find_by_folder_path(session: AsyncSession, folder_path: str) -> FolderConvention | None:
    result = await session.execute(
        select(FolderConvention).where(FolderConvention.folder_path == folder_path)
    )
    return result.scalar_one_or_none()


def _ancestor_paths(note_path: str) -> list[str]:
    """Return all ancestor folder paths for a note, from root to immediate parent.

    For "projects/active/sprint-1.md" returns:
    ["/", "projects/", "projects/active/"]
    """
    parts = note_path.rstrip("/").split("/")
    paths = ["/"]
    for i in range(len(parts) - 1):
        paths.append("/".join(parts[: i + 1]) + "/")
    return paths


async def resolve_conventions(
    session: AsyncSession, note_path: str
) -> tuple[list[str], list[FrontmatterField], list[str], list[str]]:
    """Resolve the merged convention for a note path using additive inheritance.

    Returns (merged_from, required_frontmatter, expected_tags, backlink_targets).
    Child folder entries override parent entries for the same frontmatter key.
    Tags and backlink targets are additive (union).
    """
    ancestor_paths = _ancestor_paths(note_path)
    result = await session.execute(
        select(FolderConvention)
        .where(FolderConvention.folder_path.in_(ancestor_paths))
        .order_by(FolderConvention.folder_path)
    )
    conventions = list(result.scalars().all())

    if not conventions:
        return [], [], [], []

    merged_from: list[str] = []
    frontmatter_by_key: dict[str, dict] = {}
    tags: set[str] = set()
    backlinks: set[str] = set()

    for conv in conventions:
        merged_from.append(conv.folder_path)
        for field in conv.required_frontmatter:
            # Child overrides parent for same key
            frontmatter_by_key[field["key"]] = field
        tags.update(conv.expected_tags)
        backlinks.update(conv.backlink_targets)

    merged_frontmatter = [
        FrontmatterField(key=f["key"], default_value=f.get("default_value"))
        for f in frontmatter_by_key.values()
    ]

    return merged_from, merged_frontmatter, sorted(tags), sorted(backlinks)
