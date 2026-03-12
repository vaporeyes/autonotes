# ABOUTME: Route modules and shared error handling for the orchestrator API.
# ABOUTME: Each module handles a resource group (notes, patches, commands, jobs, ai, logs, health).

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str, context: dict | None = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.context = context or {}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "context": exc.context,
        },
    )


# Standard error factory functions
def not_found(detail: str, **ctx) -> AppError:
    return AppError(404, detail, "NOT_FOUND", ctx)


def conflict(detail: str, **ctx) -> AppError:
    return AppError(409, detail, "CONFLICT", ctx)


def obsidian_unreachable(detail: str = "Obsidian REST API unreachable") -> AppError:
    return AppError(502, detail, "OBSIDIAN_UNREACHABLE")


def obsidian_error(detail: str, **ctx) -> AppError:
    return AppError(502, detail, "OBSIDIAN_ERROR", ctx)


def validation_error(detail: str, **ctx) -> AppError:
    return AppError(422, detail, "VALIDATION_ERROR", ctx)


def llm_error(detail: str, **ctx) -> AppError:
    return AppError(502, detail, "LLM_ERROR", ctx)
