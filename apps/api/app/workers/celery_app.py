"""Claustor AI — Celery Configuration."""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

_broker_url = (
    getattr(settings, "RABBITMQ_URL", None)
    or getattr(settings, "UPSTASH_REDIS_URL", None)
    or "redis://localhost:6379/0"
)

app = Celery(
    "claustor",
    broker=_broker_url,
    backend="rpc://",
    include=[
        "app.workers.tasks.alert_tasks",
        "app.workers.tasks.contract_tasks",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=True,
)

app.conf.beat_scheduler = "celery.beat.PersistentScheduler"
app.conf.beat_schedule_filename = "/tmp/claustor-celerybeat-schedule"
app.conf.beat_schedule = {
    "daily-alerts": {
        "task": "app.workers.tasks.alert_tasks.run_daily_alerts",
        "schedule": crontab(hour=9, minute=0),
    },
    "monthly-usage-reset": {
        "task": "app.workers.tasks.alert_tasks.reset_monthly_usage",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
    },
    "cleanup-expired-guests": {
        "task": "app.workers.tasks.alert_tasks.cleanup_expired_guests",
        "schedule": crontab(hour=1, minute=0),
    },
}
