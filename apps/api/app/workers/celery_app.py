"""
Claustor AI — Celery Configuration

Queue routing by plan:
  free_queue        → 1 worker  (low priority)
  starter_queue     → 2 workers (normal)
  pro_queue         → 4 workers (high priority)
  enterprise_queue  → 8 workers (highest)

Start workers:
  # All queues (dev):
  celery -A app.workers.celery_app worker --loglevel=info \
    -Q free_queue,starter_queue,pro_queue,enterprise_queue \
    --concurrency=4

  # Production (separate workers per plan):
  celery -A app.workers.celery_app worker -Q free_queue --concurrency=1 -n free@%h
  celery -A app.workers.celery_app worker -Q starter_queue --concurrency=2 -n starter@%h
  celery -A app.workers.celery_app worker -Q pro_queue --concurrency=4 -n pro@%h
  celery -A app.workers.celery_app worker -Q enterprise_queue --concurrency=8 -n enterprise@%h
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange
from app.core.config import settings

# ── Broker ───────────────────────────────────────────
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

# ── Plan-based queues ────────────────────────────────
default_exchange = Exchange("claustor", type="direct")

app.conf.task_queues = (
    Queue("free_queue",        default_exchange, routing_key="free",         queue_arguments={"x-max-priority": 1}),
    Queue("starter_queue",     default_exchange, routing_key="starter",      queue_arguments={"x-max-priority": 5}),
    Queue("pro_queue",         default_exchange, routing_key="professional", queue_arguments={"x-max-priority": 8}),
    Queue("enterprise_queue",  default_exchange, routing_key="enterprise",   queue_arguments={"x-max-priority": 10}),
    Queue("alerts",            default_exchange, routing_key="alerts"),
)

app.conf.task_default_queue    = "starter_queue"
app.conf.task_default_exchange = "claustor"
app.conf.task_default_routing_key = "starter"

# Route tasks to correct queues
app.conf.task_routes = {
    "app.workers.tasks.contract_tasks.process_contract": {
        "queue": "starter_queue",  # default, overridden per-task via apply_async
    },
    "app.workers.tasks.alert_tasks.*": {
        "queue": "alerts",
    },
}

# ── Config ───────────────────────────────────────────
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
    task_compression="gzip",
)

# ── Beat Schedule ────────────────────────────────────
app.conf.beat_scheduler = "celery.beat.PersistentScheduler"
app.conf.beat_schedule_filename = "/tmp/claustor-celerybeat-schedule"
app.conf.beat_schedule = {
    "daily-alerts": {
        "task":     "app.workers.tasks.alert_tasks.run_daily_alerts",
        "schedule": crontab(hour=9, minute=0),
        "options":  {"queue": "alerts"},
    },
    "monthly-usage-reset": {
        "task":     "app.workers.tasks.alert_tasks.reset_monthly_usage",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
        "options":  {"queue": "alerts"},
    },
    "cleanup-expired-guests": {
        "task":     "app.workers.tasks.alert_tasks.cleanup_expired_guests",
        "schedule": crontab(hour=1, minute=0),
        "options":  {"queue": "alerts"},
    },
}
