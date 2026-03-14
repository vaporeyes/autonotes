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

    # Auto-triage
    triage_scan_cron: str = "0 5 * * *"  # Daily at 5am UTC
    triage_scan_scope: str = "/"

    # Note similarity engine
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_exclude_patterns: str = "90 Atlas/Templates/,Attachments/,images/"
    embedding_batch_size: int = 50
    similarity_default_threshold: float = 0.5
    duplicate_default_threshold: float = 0.9
    cluster_min_size: int = 3
    moc_target_folder: str = "30 Maps/"
    embedding_scan_cron: str = "0 4 * * *"  # Daily at 4am UTC
    cluster_scan_cron: str = "0 4 1 * *"  # Monthly on the 1st at 4am UTC


settings = Settings()
