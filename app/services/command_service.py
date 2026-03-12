# ABOUTME: Service for listing and executing Obsidian commands via the REST API.
# ABOUTME: Logs command executions through the operation log service.

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import LogStatus
from app.services import log_service
from app.services.obsidian_client import obsidian_client


async def list_commands() -> list[dict]:
    return await obsidian_client.list_commands()


async def execute_command(command_id: str, session: AsyncSession) -> None:
    await obsidian_client.execute_command(command_id)
    await log_service.create_log(
        session,
        operation_name=f"execute_command:{command_id}",
        target_path="obsidian://commands",
        status=LogStatus.success,
    )
