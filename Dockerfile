# ABOUTME: Multi-stage Docker build for the Autonotes orchestrator.
# ABOUTME: Shared image for both the FastAPI api and Celery worker services.

FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
