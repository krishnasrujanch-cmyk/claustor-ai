# Claustor AI

**The AI-Powered Contract Intelligence Platform**

> claustor.com — Transforming Contracts into Intelligence

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/krishnasrujanch-cmyk/claustor-ai
cd claustor-ai

# 2. Setup
make setup          # installs all dependencies

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Start infrastructure
make dev:infra      # postgres + redis + rabbitmq

# 5. Run migrations
make migrate

# 6. Start everything
make dev            # api + web + worker
```

**Services:**
- API:       http://localhost:8000
- Web:       http://localhost:3000
- API Docs:  http://localhost:8000/docs
- RabbitMQ:  http://localhost:15672 (claustor/claustor_dev)

---

## Architecture

```
claustor-ai/
├── apps/
│   ├── api/        FastAPI backend (Python 3.12)
│   ├── web/        Next.js 14 frontend (TypeScript)
│   └── worker/     Celery workers (async processing)
├── packages/
│   ├── types/      Shared TypeScript + Python types
│   └── config/     Shared configs (ESLint, tsconfig)
├── services/
│   ├── billing/    Stripe integration
│   └── notifications/ Email, SMS, Slack
└── infrastructure/
    ├── terraform/  GCP infra as code
    └── docker/     Dockerfiles
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind, shadcn/ui |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| Database | PostgreSQL 16 (Neon.tech) |
| Vector DB | Pinecone (multi-tenant namespaces) |
| Cache | Redis (Upstash) |
| Queue | RabbitMQ (CloudAMQP) |
| LLM | Groq → Gemini → OpenAI (abstracted) |
| Auth | Auth0 + JWT |
| Storage | Google Cloud Storage |

## Development Commands

```bash
make help           # show all commands
make dev            # start everything
make test           # run all tests
make migrate        # run DB migrations
make lint           # lint all code
make format         # format all code
```

## LLM Provider Migration

To switch from Groq to Gemini — just update `.env`:

```bash
GROQ_API_KEY=       # empty = disabled
GEMINI_API_KEY=AIzaSy_xxx  # now primary
```

Zero code changes required.

---

*Built by Srujan Krishna, DKU Technologies*
*© 2026 Claustor AI — claustor.com*
