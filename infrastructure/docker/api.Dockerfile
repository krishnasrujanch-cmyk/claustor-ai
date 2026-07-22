# ═══════════════════════════════════════════════════
# Claustor AI — API Dockerfile
# Multi-stage build for development and production
# ═══════════════════════════════════════════════════

# ── Base ──────────────────────────────────────────
FROM python:3.12-slim AS base

# Security: run as non-root user
RUN groupadd -r claustor && useradd -r -g claustor claustor

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libstdc++6 \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-tam \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependencies ──────────────────────────────────
FROM base AS dependencies
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Development ───────────────────────────────────
FROM dependencies AS development
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=development

COPY apps/api/ .
RUN chown -R claustor:claustor /app
USER claustor

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production ────────────────────────────────────
FROM dependencies AS production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

COPY apps/api/ .
RUN chown -R claustor:claustor /app
USER claustor

EXPOSE 8000
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info", \
     "--no-access-log"]
