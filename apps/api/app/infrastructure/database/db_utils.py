"""
Claustor AI — DB Utilities for Long-Running Pipelines
Implements industry patterns for reliable DB operations in async pipelines.

Pattern 2: Connection health check before use
Pattern 3: Retry decorator on DB operations
"""
from __future__ import annotations
import asyncio
import functools
import structlog
from typing import Callable, TypeVar, Any
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

T = TypeVar("T")


async def is_connection_alive(db: AsyncSession) -> bool:
    """Pattern 2: Check if DB connection is alive before use."""
    try:
        await db.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        return False


async def db_op_with_retry(
    session_factory: async_sessionmaker,
    operation: Callable[[AsyncSession], Any],
    max_retries: int = 3,
    retry_delay: float = 1.0,
    operation_name: str = "db_operation",
) -> Any:
    """
    Pattern 2 + 3: Execute DB operation with health check and retry.
    
    - Opens fresh session per attempt (Pattern 1)
    - Checks connection health before executing (Pattern 2)
    - Retries on InterfaceError/connection errors (Pattern 3)
    
    Usage:
        result = await db_op_with_retry(
            session_factory,
            lambda db: db.execute(text("UPDATE contracts SET status=:s WHERE id=:id"), ...),
            operation_name="update_contract_status"
        )
    """
    from sqlalchemy.exc import InterfaceError, OperationalError, DisconnectionError

    last_exc = None
    for attempt in range(max_retries):
        try:
            # Pattern 1: Fresh session per operation
            async with session_factory() as db:
                # Pattern 2: Health check before use
                if not await is_connection_alive(db):
                    logger.warning("db_connection_dead_reconnecting",
                                   operation=operation_name, attempt=attempt)
                    await db.close()
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue

                result = await operation(db)
                await db.commit()
                if attempt > 0:
                    logger.info("db_op_succeeded_after_retry",
                               operation=operation_name, attempt=attempt)
                return result

        except (InterfaceError, OperationalError, DisconnectionError) as e:
            # Pattern 3: Retry on connection errors
            last_exc = e
            logger.warning("db_connection_error_retrying",
                          operation=operation_name,
                          attempt=attempt,
                          max_retries=max_retries,
                          error=str(e)[:200])
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
        except Exception as e:
            # Also handle PendingRollbackError
            from sqlalchemy.exc import PendingRollbackError
            if "PendingRollbackError" in type(e).__name__ or "rollback" in str(e).lower():
                last_exc = e
                logger.warning("db_pending_rollback_retrying",
                              operation=operation_name, attempt=attempt)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
            logger.error("db_op_failed_non_retryable",
                        operation=operation_name, error=str(e))
            raise

    raise last_exc or RuntimeError(f"DB operation {operation_name} failed after {max_retries} retries")


def with_fresh_session(session_factory_attr: str = "_session_factory"):
    """
    Pattern 1 + 4 decorator: Ensures method always uses a fresh DB session.
    Prevents holding sessions across long IO-bound operations.
    
    Usage:
        @with_fresh_session("session_factory")
        async def _save_results(self, db, ...):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, db, *args, **kwargs):
            factory = getattr(self, session_factory_attr, None)
            if factory is None:
                # Fallback: use passed db directly
                return await func(self, db, *args, **kwargs)
            # Open fresh session, ignore passed db
            async with factory() as fresh_db:
                return await func(self, fresh_db, *args, **kwargs)
        return wrapper
    return decorator
