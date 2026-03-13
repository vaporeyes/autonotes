# ABOUTME: Celery application singleton with Redis broker and result backend.
# ABOUTME: Autodiscovers tasks from app.tasks package.

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "autonotes",
    broker=settings.redis_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.vault_scan",
        "app.tasks.vault_cleanup",
        "app.tasks.ai_analysis",
        "app.tasks.log_purge",
        "app.tasks.vault_health_scan",
        "app.tasks.triage_scan",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

def _parse_cron(expr: str) -> crontab:
    """Parse a 5-field cron expression into a Celery crontab."""
    parts = expr.split()
    if len(parts) != 5:
        return crontab(hour=4, minute=0)
    return crontab(
        minute=parts[0],
        hour=parts[1],
        day_of_month=parts[2],
        month_of_year=parts[3],
        day_of_week=parts[4],
    )


celery.conf.beat_schedule = {
    "purge-old-logs": {
        "task": "log_purge",
        "schedule": crontab(hour=3, minute=0),
    },
    "scheduled-health-scan": {
        "task": "vault_health_scan",
        "schedule": _parse_cron(settings.health_scan_cron),
        "args": [None, settings.health_scan_scope, None],
    },
    "purge-old-snapshots": {
        "task": "health_snapshot_purge",
        "schedule": crontab(hour=3, minute=30),
    },
    "scheduled-triage-scan": {
        "task": "triage_scan",
        "schedule": _parse_cron(settings.triage_scan_cron),
        "args": [None, settings.triage_scan_scope, None],
    },
}
