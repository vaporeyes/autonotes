# ABOUTME: FastAPI application factory with lifespan handler for startup/shutdown.
# ABOUTME: Mounts all route modules under /api/v1 prefix.

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import AppError, app_error_handler, health
from app.api.routes import ai, commands, jobs, logs, notes, patches


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Autonotes AI Orchestrator",
        description="AI-powered orchestrator for Obsidian vault management. "
        "Read and analyze notes, apply surgical patches, execute Obsidian commands, "
        "run background vault scans, and interact with vault content via LLM.",
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Notes", "description": "Read and analyze vault notes and folders"},
            {"name": "Patches", "description": "Submit, approve, and reject surgical patch operations"},
            {"name": "Commands", "description": "List and execute Obsidian commands"},
            {"name": "Jobs", "description": "Submit and track background jobs (scans, cleanup, AI analysis)"},
            {"name": "AI", "description": "LLM-powered analysis, suggestions, and chat"},
            {"name": "Logs", "description": "Query operation audit logs"},
            {"name": "Health", "description": "System health and connectivity checks"},
        ],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(notes.router, prefix="/api/v1")
    app.include_router(patches.router, prefix="/api/v1")
    app.include_router(commands.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")
    app.include_router(logs.router, prefix="/api/v1")

    return app


app = create_app()
