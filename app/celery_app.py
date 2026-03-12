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

celery.conf.beat_schedule = {
    "purge-old-logs": {
        "task": "log_purge",
        "schedule": crontab(hour=3, minute=0),
    },
}
