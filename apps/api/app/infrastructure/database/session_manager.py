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
    "authentication timed out",
    "protocolviolationerror",
    "asyncpg.exceptions",
    "ssl connection has been closed",
    "end of file",
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
    Create a fresh engine + session factory for long-running pipeline operations.
    Uses Neon's DIRECT (non-pooled) endpoint — bypasses PgBouncer which causes
    intermittent 'Authentication timed out' errors with bursty serverless clients.
    API uses the pooled endpoint (high concurrency); worker uses direct (reliable).
    """
    # Strip -pooler from URL to use Neon's direct endpoint
    database_url = database_url.replace("-pooler.", ".")
    engine = create_async_engine(
        database_url,
        connect_args={
            "ssl": _make_ssl_context(),
            "statement_cache_size": 0,
            "timeout": 30,
            "command_timeout": 60,
        },
        pool_size=2,
        max_overflow=3,
        pool_pre_ping=True,       # Test connection before use
        pool_recycle=300,          # Recycle connections every 5 min
        pool_timeout=30,           # Wait up to 30s for a connection
        echo=False,
    )

    # Neon's pooled connection rejects search_path as a startup parameter,
    # so we set it as the first statement on every new DBAPI connection instead.
    from sqlalchemy import event as _event
    @_event.listens_for(engine.sync_engine, "connect")
    def _set_search_path(dbapi_connection, connection_record):
        dbapi_connection.run_async(lambda c: c.execute("SET search_path TO public"))

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

    def __init__(self, database_url: str, max_retries: int = 8):
        import datetime; print(f"SESSION_MGR_V2 max_retries=8 built={datetime.datetime.utcnow()}", flush=True)
        self._database_url = database_url
        self._max_retries = max_retries
        self._engine = None
        self._factory = None

    async def initialize(self) -> None:
        """Initialize engine and session factory, pre-warm connection."""
        self._engine, self._factory = make_session_factory(self._database_url)
        # Pre-warm: establish actual DB connection with retry
        for attempt in range(self._max_retries):
            try:
                async with self._engine.connect() as conn:
                    await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
                logger.info("pipeline_db_connected", attempt=attempt+1)
                break
            except Exception as e:
                wait = min(2 ** (attempt + 1), 30)
                logger.warning("pipeline_db_connect_retry",
                               attempt=attempt+1, error=str(e)[:100], wait=wait)
                if attempt < self._max_retries - 1:
                    await __import__("asyncio").sleep(wait)
                else:
                    logger.error("pipeline_db_connect_failed_all_retries")
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
                try:
                    await db.commit()
                except Exception as commit_err:
                    # NullPool connection may close during long operations
                    # If commit fails, try rollback and re-raise
                    logger.warning("session_commit_failed",
                                   error=str(commit_err)[:200])
                    try:
                        await db.rollback()
                    except Exception:
                        pass
                    raise
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
                    if attempt > 0:
                        logger.info("pipeline_db_retry_success",
                                   operation=operation_name, attempt=attempt+1)
                    return result
            except Exception as exc:
                if _is_transient(exc) and attempt < self._max_retries - 1:
                    wait = min(2 ** (attempt + 1), 30)  # Exponential backoff: 2s, 4s, 8s, 16s, 30s
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
