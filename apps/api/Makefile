# Claustor AI — Development Commands
# Usage: make <target>

.PHONY: test test-fast test-full lint run-api run-worker

# ── Testing ─────────────────────────────────────────────────────────────────

## Run before every commit (2s, no LLM cost)
test:
	pytest app/tests/eval/test_model_integrity.py -v

## Run before every release (~72s, small LLM cost)
test-full:
	pytest app/tests/eval/ -v

## Run only party identifier tests
test-party:
	pytest app/tests/eval/test_party_identifiers.py -v

## Run only judge routing tests
test-routing:
	pytest app/tests/eval/test_judge_routing.py -v

# ── Development ──────────────────────────────────────────────────────────────

## Start API server
run-api:
	source .venv/bin/activate && \
	python3 -m uvicorn app.main:app --port 8000 --reload

## Start Celery worker
run-worker:
	source .venv/bin/activate && \
	celery -A app.workers.celery_app worker --loglevel=info \
	  -Q enterprise_queue,pro_queue,starter_queue,free_queue --concurrency=1

## Run DB migrations
migrate:
	source .venv/bin/activate && alembic upgrade head

## Backfill party identifiers for existing contracts
backfill-parties:
	source .venv/bin/activate && \
	python3 -m app.scripts.backfill_party_identifiers
