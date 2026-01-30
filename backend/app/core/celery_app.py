"""
Celery application configuration
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "pentest_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.scan_tasks", "app.tasks.schedule_tasks", "app.tasks.email_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Beat schedule (for scheduled scans)
celery_app.conf.beat_schedule = {
    # Will be populated dynamically from database
}
