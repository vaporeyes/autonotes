# ABOUTME: Routes for reading and analyzing vault notes and folders.
# ABOUTME: GET /notes/{path} for single note, GET /notes/folder/{path} for folder listing.

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

from app.api.routes import not_found, obsidian_error, obsidian_unreachable
from app.schemas.note import FolderResponse, Note, NoteSummary, VaultStructureNode
from app.services.note_parser import parse_note, parse_note_summary
from app.services.obsidian_client import obsidian_client

router = APIRouter(tags=["Notes"])


@router.get("/vault-structure", response_model=VaultStructureNode)
async def get_vault_structure():
    async def build_tree(path: str, name: str) -> VaultStructureNode:
        try:
            files = await obsidian_client.list_folder(path)
        except Exception:
            return VaultStructureNode(name=name, path=path, note_count=0, children=[])

        note_count = sum(1 for f in files if f.endswith(".md"))
        children = []
        for f in files:
            # list_folder already returns full paths (e.g. "attachments/audio/")
            if f.endswith("/"):
                folder_path = f.rstrip("/")
                folder_name = folder_path.rsplit("/", 1)[-1]
                child = await build_tree(folder_path, folder_name)
                children.append(child)

        children.sort(key=lambda c: c.name)
        return VaultStructureNode(
            name=name,
            path=path + "/" if path and not path.endswith("/") else path or "/",
            note_count=note_count,
            children=children,
        )

    try:
        tree = await build_tree("", "/")
    except httpx.ConnectError:
        raise obsidian_unreachable()
    return tree


@router.get("/notes/folder/{path:path}", response_model=FolderResponse)
async def get_folder(path: str, recursive: bool = False):
    try:
        files = await obsidian_client.list_folder(path, recursive=recursive)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise not_found(f"Folder not found: {path}", target_path=path)
        raise obsidian_error(f"Obsidian API error: {exc.response.status_code}", target_path=path)
    except httpx.ConnectError:
        raise obsidian_unreachable()

    md_files = [f for f in files if f.endswith(".md")]
    notes: list[NoteSummary] = []

    for file_path in md_files:
        try:
            raw = await obsidian_client.get_note_raw(file_path)
            summary = parse_note_summary(file_path, raw)
            notes.append(summary)
        except Exception:
            continue

    folder_display = path if path.endswith("/") else path + "/"
    return FolderResponse(folder=folder_display, note_count=len(notes), notes=notes)


@router.get("/notes/{path:path}", response_model=Note)
async def get_note(path: str):
    try:
        raw = await obsidian_client.get_note_raw(path)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise not_found(f"Note not found: {path}", target_path=path)
        raise obsidian_error(f"Obsidian API error: {exc.response.status_code}", target_path=path)
    except httpx.ConnectError:
        raise obsidian_unreachable()

    try:
        json_data = await obsidian_client.get_note(path)
        stat = json_data.get("stat", {})
        mtime = stat.get("mtime")
        last_modified = datetime.fromtimestamp(mtime / 1000, tz=timezone.utc) if mtime else None
    except Exception:
        last_modified = None

    return parse_note(path, raw, last_modified)
