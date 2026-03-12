# ABOUTME: Routes for listing and executing Obsidian commands.
# ABOUTME: GET /commands lists available commands, POST /commands/{id} executes one.

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import not_found, obsidian_unreachable
from app.db.session import get_session
from app.services import command_service

router = APIRouter(tags=["Commands"])


@router.get("/commands")
async def list_commands():
    try:
        commands = await command_service.list_commands()
    except httpx.ConnectError:
        raise obsidian_unreachable()
    return {"commands": commands}


@router.post("/commands/{command_id}")
async def execute_command(command_id: str, session: AsyncSession = Depends(get_session)):
    try:
        await command_service.execute_command(command_id, session)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise not_found(f"Unknown command: {command_id}")
        raise
    except httpx.ConnectError:
        raise obsidian_unreachable()

    await session.commit()
    return {"command_id": command_id, "status": "executed"}
