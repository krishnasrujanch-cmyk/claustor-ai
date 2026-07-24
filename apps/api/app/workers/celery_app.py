"""
Claustor AI — Celery Configuration
Background task workers + Beat scheduler.

Workers: process contracts, send alerts
Beat:    daily alert scheduler (9 AM IST)

Start worker:  celery -A app.workers.celery_app worker --loglevel=info
Start beat:    celery -A app.workers.celery_app beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

app = Celery(
    "claustor",
    broker=settings.CLOUDAMQP_URL,
    backend="redis://" + settings.UPSTASH_REDIS_URL.replace("rediss://default:", "").replace("redis://default:", ""),
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
)

# ── Beat Schedule ────────────────────────────────────
app.conf.beat_schedule = {
    # Run daily alerts at 9 AM IST
    "daily-alerts": {
        "task":     "app.workers.tasks.alert_tasks.run_daily_alerts",
        "schedule": crontab(hour=9, minute=0),
    },
    # Reset monthly usage on 1st of every month
    "monthly-usage-reset": {
        "task":     "app.workers.tasks.alert_tasks.reset_monthly_usage",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
    },
    # Clean up expired guest users daily
    "cleanup-expired-guests": {
        "task":     "app.workers.tasks.alert_tasks.cleanup_expired_guests",
        "schedule": crontab(hour=1, minute=0),
    },
}
