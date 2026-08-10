#!/bin/bash
exec celery -A app.workers.celery_app worker \
    --loglevel=info \
    -Q enterprise_queue,pro_queue,starter_queue,free_queue,alerts \
    --concurrency=2 \
    --max-tasks-per-child=100
