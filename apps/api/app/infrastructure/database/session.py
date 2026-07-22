"""
Claustor AI — Database Session Management
Async SQLAlchemy with connection pooling.
Multi-tenant: every query scoped to org_id.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession,
    async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ── Engine ────────────────────────────────────────────────
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker | None = None


async def init_db() -> None:
    """Initialize database engine and session factory."""
    global engine, async_session_factory

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,   # verify connections before use
        echo=settings.ENVIRONMENT == "development",
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    # Verify connection
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: c.execute(
            __import__("sqlalchemy").text("SELECT 1")
        ))

    logger.info("database_pool_initialized", pool_size=settings.DATABASE_POOL_SIZE)


async def close_db() -> None:
    """Close database connection pool."""
    if engine:
        await engine.dispose()
        logger.info("database_pool_closed")


# ── Session Dependency ────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session.
    Auto-commits on success, rolls back on error.

    Usage:
        @router.get("/")
        async def my_endpoint(db: DbSession):
            ...
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Type alias for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]


# ── Base Model ────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass
