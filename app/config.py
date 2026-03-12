# ABOUTME: Application settings loaded from environment variables via pydantic-settings.
# ABOUTME: Central configuration for Obsidian API, database, Redis, LLM, and log retention.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Obsidian Local REST API
    obsidian_api_url: str = "https://host.docker.internal:27124"
    obsidian_api_key: str = ""

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://autonotes:autonotes@postgres:5432/autonotes"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # LLM provider
    llm_provider: str = "claude"
    llm_api_key: str = ""

    # Operation log retention
    log_retention_days: int = 90


settings = Settings()
