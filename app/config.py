# ABOUTME: Application settings loaded from environment variables via pydantic-settings.
# ABOUTME: Central configuration for Obsidian API, database, Redis, LLM, and log retention.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Obsidian Local REST API
    obsidian_api_url: str = "http://host.docker.internal:27123"
    obsidian_api_key: str = ""

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://autonotes:autonotes@postgres:5432/autonotes"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # LLM provider (claude, openai, or openrouter)
    llm_provider: str = "claude"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""

    # Operation log retention
    log_retention_days: int = 90

    # Vault health analytics
    health_scan_cron: str = "0 4 * * *"  # Daily at 4am UTC
    health_scan_scope: str = "/"
    health_stale_threshold_hours: int = 24


settings = Settings()
