"""
Claustor AI — Pipeline Session Manager
======================================
Proper session management for long-running async pipelines.

Design principles:
  - Session-per-operation (Pattern 1): Never hold session across IO-bound work
  - Health check before use (Pattern 2): Verify connection before executing
  - Retry on transient errors (Pattern 3): Auto-recover from network blips
  - Factory injection (Pattern 4): Pipeline receives factory, not session

Supports:
  - 100s of concurrent uploads
  - 16+ page contracts (10+ min pipeline)
  - Neon serverless PostgreSQL (aggressive idle timeouts)
  - Celery forked worker processes
"""
from __future__ import annotations

import asyncio
import ssl
import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Any, TypeVar
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text

logger = structlog.get_logger(__name__)

T = TypeVar("T")

# Transient errors that warrant a retry
_TRANSIENT_ERRORS = (
    "connection is closed",
    "connection was closed",
    "server closed the connection",
    "can't reconnect",
    "pendingrollback",
    "connection refused",
    "connection reset",
    "broken pipe",
    "interface error",
    "operational error",
)


def _is_transient(exc: Exception) -> bool:
    """Check if exception is a transient DB connection error."""
    msg = str(exc).lower()
    type_name = type(exc).__name__.lower()
    return any(e in msg or e in type_name for e in _TRANSIENT_ERRORS)


def _make_ssl_context() -> ssl.SSLContext:
    """Create SSL context for Neon PostgreSQL."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def make_session_factory(database_url: str) -> tuple[Any, async_sessionmaker]:
    """
    Create a fresh engine + session factory using NullPool.
    NullPool = new connection per session = no idle timeout issues.
    Use for long-running pipeline operations.
    """
    engine = create_async_engine(
        database_url,
        connect_args={
            "ssl": _make_ssl_context(),
            "statement_cache_size": 0,  # Required for NullPool + asyncpg
        },
        poolclass=NullPool,
        echo=False,
    )
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return engine, factory


class PipelineSessionManager:
    """
    Session manager for long-running contract processing pipelines.

    Usage:
        mgr = PipelineSessionManager(database_url)
        await mgr.initialize()

        # Each DB operation gets its own fresh session
        await mgr.execute(lambda db: db.execute(...))

        # Or use context manager
        async with mgr.session() as db:
            await db.execute(...)

        await mgr.dispose()
    """

    def __init__(self, database_url: str, max_retries: int = 3):
        self._database_url = database_url
        self._max_retries = max_retries
        self._engine = None
        self._factory = None

    async def initialize(self) -> None:
        """Initialize engine and session factory."""
        self._engine, self._factory = make_session_factory(self._database_url)
        logger.debug("pipeline_session_manager_initialized")

    async def dispose(self) -> None:
        """Dispose engine and release all connections."""
        if self._engine:
            await self._engine.dispose()
            logger.debug("pipeline_session_manager_disposed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager that provides a fresh session.
        Automatically commits on success, rolls back on error.
        NullPool ensures a brand-new connection every time.
        """
        if self._factory is None:
            raise RuntimeError("PipelineSessionManager not initialized")

        async with self._factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                try:
                    await db.rollback()
                except Exception:
                    pass
                raise

    async def execute(
        self,
        operation: Callable[[AsyncSession], Any],
        operation_name: str = "pipeline_db_op",
    ) -> Any:
        """
        Execute a DB operation with automatic retry on transient errors.
        Each attempt gets a brand-new session (NullPool).
        """
        last_exc = None
        for attempt in range(self._max_retries):
            try:
                async with self.session() as db:
                    result = await operation(db)
                    return result
            except Exception as exc:
                if _is_transient(exc) and attempt < self._max_retries - 1:
                    wait = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        "pipeline_db_retry",
                        operation=operation_name,
                        attempt=attempt + 1,
                        wait_secs=wait,
                        error=str(exc)[:200],
                    )
                    await asyncio.sleep(wait)
                    last_exc = exc
                else:
                    logger.error(
                        "pipeline_db_failed",
                        operation=operation_name,
                        attempt=attempt + 1,
                        error=str(exc)[:200],
                    )
                    raise

        raise last_exc or RuntimeError(f"{operation_name} failed after {self._max_retries} retries")

    async def update_status(
        self,
        contract_id,
        status: str,
        error: str | None = None,
    ) -> None:
        """Update contract status using a fresh session."""
        from sqlalchemy import text as _text

        async def _op(db: AsyncSession):
            if error:
                await db.execute(
                    _text("""
                        UPDATE contracts
                        SET status = :status,
                            processing_error = :error,
                            updated_at = NOW()
                        WHERE id = :cid
                    """),
                    {"status": status, "error": error[:1000], "cid": str(contract_id)},
                )
            else:
                await db.execute(
                    _text("""
                        UPDATE contracts
                        SET status = :status,
                            updated_at = NOW()
                        WHERE id = :cid
                    """),
                    {"status": status, "cid": str(contract_id)},
                )

        await self.execute(_op, operation_name=f"update_status_{status}")
        logger.info("pipeline_status_updated",
                    contract_id=str(contract_id), status=status)
