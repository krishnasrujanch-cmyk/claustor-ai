"""
Claustor AI — FastAPI Application Entry Point
Production-grade, multi-tenant contract intelligence platform.
"""

from contextlib import asynccontextmanager

import structlog
from app.infrastructure.document.processor import DocumentProcessor
from fastapi import FastAPI
from app.middleware.rate_limit import rate_limit_middleware, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.infrastructure.database.session import init_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # ── Startup ──────────────────────────────────
    setup_logging()
    logger.info(
        "claustor_starting",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
    )

    # Initialize database connection pool
    await init_db(settings.DATABASE_URL)
    logger.info("database_connected")

    # Load document processing models (once at startup)
    # Runs in thread pool to avoid blocking event loop during 400MB model load
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, DocumentProcessor.init_models)

    # Pre-load embedding model at startup (bge-large ~1.3GB, load once)
    try:
        from app.infrastructure.vector_store.pinecone_store import get_vector_store
        _store = get_vector_store()
        await _store.get_embedder()
        logger.info("embedding_model_preloaded")
    except Exception as _e:
        logger.warning(f"embedding_model_preload_failed: {_e}")

    # Pre-load cross-encoder reranker at startup
    try:
        from app.agents.rag.reranker import _load_reranker
        await loop.run_in_executor(None, _load_reranker)
        logger.info("reranker_preloaded")
    except Exception as _e:
        logger.warning(f"reranker_preload_failed: {_e}")

    yield

    # ── Shutdown ──────────────────────────────────
    logger.info("claustor_shutting_down")


def create_application() -> FastAPI:
    """Application factory — creates and configures FastAPI app."""

    app = FastAPI(
        title="Claustor AI",
        description="The AI-Powered Contract Intelligence Platform",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # ── Security Middleware ───────────────────────
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["claustor.com", "*.claustor.com", "claustor-api-*.run.app"],
        )

    # ── CORS ─────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    # ── Routes ───────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Health check (no auth required) ──────────
    @app.get("/health", tags=["system"])
    async def health_check():
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": settings.APP_VERSION,
        }

    # ── Global exception handler ──────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


app = create_application()
