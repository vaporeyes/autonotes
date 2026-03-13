# ABOUTME: CRUD routes for folder conventions and inheritance resolution endpoint.
# ABOUTME: POST, GET, PUT, DELETE for conventions plus GET /resolve for merged lookup.

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import conflict, not_found
from app.db.session import get_session
from app.schemas.convention import (
    ConventionCreate,
    ConventionListResponse,
    ConventionResponse,
    ConventionUpdate,
    ResolvedConvention,
)
from app.services import convention_service

router = APIRouter(tags=["Conventions"])


def _to_response(conv) -> ConventionResponse:
    return ConventionResponse(
        id=str(conv.id),
        folder_path=conv.folder_path,
        required_frontmatter=conv.required_frontmatter,
        expected_tags=conv.expected_tags,
        backlink_targets=conv.backlink_targets,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.post("/conventions", response_model=ConventionResponse, status_code=201)
async def create_convention(req: ConventionCreate, session: AsyncSession = Depends(get_session)):
    existing = await convention_service.find_by_folder_path(session, req.folder_path)
    if existing:
        raise conflict(f"Convention already exists for folder: {req.folder_path}")

    conv = await convention_service.create_convention(
        session,
        folder_path=req.folder_path,
        required_frontmatter=[f.model_dump() for f in req.required_frontmatter],
        expected_tags=req.expected_tags,
        backlink_targets=req.backlink_targets,
    )
    await session.commit()
    return _to_response(conv)


@router.get("/conventions", response_model=ConventionListResponse)
async def list_conventions(session: AsyncSession = Depends(get_session)):
    conventions = await convention_service.list_conventions(session)
    return ConventionListResponse(conventions=[_to_response(c) for c in conventions])


@router.get("/conventions/resolve", response_model=ResolvedConvention)
async def resolve_convention(path: str, session: AsyncSession = Depends(get_session)):
    merged_from, frontmatter, tags, backlinks = await convention_service.resolve_conventions(
        session, path
    )
    return ResolvedConvention(
        note_path=path,
        merged_from=merged_from,
        required_frontmatter=frontmatter,
        expected_tags=tags,
        backlink_targets=backlinks,
    )


@router.get("/conventions/{convention_id}", response_model=ConventionResponse)
async def get_convention(convention_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    conv = await convention_service.get_convention(session, convention_id)
    if not conv:
        raise not_found(f"Convention not found: {convention_id}")
    return _to_response(conv)


@router.put("/conventions/{convention_id}", response_model=ConventionResponse)
async def update_convention(
    convention_id: uuid.UUID, req: ConventionUpdate, session: AsyncSession = Depends(get_session)
):
    conv = await convention_service.get_convention(session, convention_id)
    if not conv:
        raise not_found(f"Convention not found: {convention_id}")

    conv = await convention_service.update_convention(
        session,
        conv,
        folder_path=req.folder_path,
        required_frontmatter=[f.model_dump() for f in req.required_frontmatter],
        expected_tags=req.expected_tags,
        backlink_targets=req.backlink_targets,
    )
    await session.commit()
    return _to_response(conv)


@router.delete("/conventions/{convention_id}", status_code=204)
async def delete_convention(
    convention_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    conv = await convention_service.get_convention(session, convention_id)
    if not conv:
        raise not_found(f"Convention not found: {convention_id}")
    await convention_service.delete_convention(session, conv)
    await session.commit()
