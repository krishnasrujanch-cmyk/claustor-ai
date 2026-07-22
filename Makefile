.PHONY: dev stop build test lint format clean setup migrate seed logs help

# ═══════════════════════════════════════════════════
# Claustor AI — Developer Commands
# ═══════════════════════════════════════════════════

# Colors
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

help: ## Show this help
	@echo "$(CYAN)Claustor AI — Developer Commands$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

# ── Development ──────────────────────────────────
setup: ## First-time setup (install all deps)
	@echo "$(CYAN)Setting up Claustor AI...$(RESET)"
	cp -n .env.example .env || true
	pnpm install
	cd apps/api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd apps/worker && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
	@echo "$(GREEN)✅ Setup complete! Edit .env with your credentials$(RESET)"

dev: ## Start all services (API + Worker + Web + infra)
	@echo "$(CYAN)Starting Claustor AI development environment...$(RESET)"
	docker compose up -d postgres redis rabbitmq
	@echo "$(YELLOW)Waiting for services...$(RESET)"
	sleep 3
	turbo run dev --parallel

dev:infra: ## Start only infrastructure (postgres, redis, rabbitmq)
	docker compose up -d postgres redis rabbitmq
	@echo "$(GREEN)✅ Infrastructure started$(RESET)"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis:      localhost:6379"
	@echo "  RabbitMQ:   localhost:5672 (UI: http://localhost:15672)"

dev:api: ## Start only the API
	turbo run dev --filter=api

dev:web: ## Start only the web app
	turbo run dev --filter=web

dev:worker: ## Start only the Celery worker
	turbo run dev --filter=worker

stop: ## Stop all services
	docker compose down
	@echo "$(GREEN)✅ All services stopped$(RESET)"

stop:clean: ## Stop and remove all data volumes
	docker compose down -v
	@echo "$(YELLOW)⚠️  All data volumes removed$(RESET)"

# ── Database ─────────────────────────────────────
migrate: ## Run database migrations
	cd apps/api && .venv/bin/alembic upgrade head
	@echo "$(GREEN)✅ Migrations applied$(RESET)"

migrate:create: ## Create new migration (usage: make migrate:create name=add_users)
	cd apps/api && .venv/bin/alembic revision --autogenerate -m "$(name)"

migrate:down: ## Rollback last migration
	cd apps/api && .venv/bin/alembic downgrade -1

seed: ## Seed database with sample data
	cd apps/api && .venv/bin/python scripts/seed.py
	@echo "$(GREEN)✅ Database seeded$(RESET)"

# ── Testing ──────────────────────────────────────
test: ## Run all tests
	turbo run test

test:api: ## Run API tests only
	cd apps/api && .venv/bin/pytest tests/ -v --cov=app --cov-report=term-missing

test:api:unit: ## Run API unit tests only
	cd apps/api && .venv/bin/pytest tests/unit/ -v

test:api:integration: ## Run API integration tests
	cd apps/api && .venv/bin/pytest tests/integration/ -v

test:web: ## Run web tests
	turbo run test --filter=web

# ── Code Quality ──────────────────────────────────
lint: ## Lint all code
	turbo run lint
	cd apps/api && .venv/bin/ruff check .
	cd apps/api && .venv/bin/mypy app/

format: ## Format all code
	pnpm prettier --write "**/*.{ts,tsx,js,jsx,json,md}"
	cd apps/api && .venv/bin/ruff format .
	cd apps/worker && .venv/bin/ruff format .

# ── Docker ───────────────────────────────────────
build: ## Build all Docker images
	docker build -f infrastructure/docker/api.Dockerfile -t claustor-api:latest .
	docker build -f infrastructure/docker/worker.Dockerfile -t claustor-worker:latest .
	@echo "$(GREEN)✅ Docker images built$(RESET)"

logs: ## View logs (usage: make logs service=api)
	docker compose logs -f $(service)

# ── Utilities ────────────────────────────────────
clean: ## Clean build artifacts
	turbo run clean
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cleaned$(RESET)"

gcp:enable: ## Enable all required GCP APIs
	gcloud services enable \
		run.googleapis.com \
		cloudbuild.googleapis.com \
		artifactregistry.googleapis.com \
		secretmanager.googleapis.com \
		storage.googleapis.com \
		certificatemanager.googleapis.com \
		iam.googleapis.com \
		logging.googleapis.com \
		monitoring.googleapis.com
	@echo "$(GREEN)✅ GCP APIs enabled$(RESET)"

gcp:deploy:api: ## Deploy API to Cloud Run
	gcloud run deploy claustor-api \
		--image asia-south1-docker.pkg.dev/contract-intelligence-p2/claustor/api:latest \
		--region asia-south1 \
		--platform managed \
		--allow-unauthenticated \
		--min-instances 0 \
		--max-instances 10 \
		--memory 2Gi \
		--cpu 2
