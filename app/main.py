# ABOUTME: FastAPI application factory with lifespan handler for startup/shutdown.
# ABOUTME: Mounts all route modules under /api/v1 prefix and serves the web dashboard.

import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import AppError, app_error_handler, health
from app.api.routes import ai, batch_patches, clusters, commands, conventions, jobs, logs, notes, patches, similarity, triage, vault_health


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
            {"name": "Conventions", "description": "Folder convention CRUD and inheritance resolution"},
            {"name": "Triage", "description": "Auto-triage scan results and history"},
            {"name": "Similarity", "description": "Note similarity search and duplicate detection"},
            {"name": "Clusters", "description": "Topic clusters and MOC generation"},
            {"name": "Batch Patches", "description": "Batch patch operations across multiple notes"},
            {"name": "Embeddings", "description": "Embedding index status and management"},
            {"name": "Vault Health", "description": "Vault health analytics, trends, and dashboard"},
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
    app.include_router(conventions.router, prefix="/api/v1")
    app.include_router(triage.router, prefix="/api/v1")
    app.include_router(similarity.router, prefix="/api/v1")
    app.include_router(batch_patches.router, prefix="/api/v1")
    app.include_router(clusters.router, prefix="/api/v1")
    app.include_router(vault_health.router, prefix="/api/v1")
    app.include_router(logs.router, prefix="/api/v1")

    # Mount web dashboard static files
    static_dir = pathlib.Path(__file__).parent / "static"
    app.mount("/dashboard", StaticFiles(directory=str(static_dir), html=True), name="dashboard")

    return app


app = create_app()
