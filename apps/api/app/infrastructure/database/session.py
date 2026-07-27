"""
Claustor AI — Database Session Management
"""

import ssl
from collections.abc import AsyncGenerator
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = structlog.get_logger(__name__)

async_session_factory: Optional[async_sessionmaker] = None


class Base(DeclarativeBase):
    pass


async def init_db(database_url: str, connect_args: dict = None) -> None:
    global async_session_factory
    if connect_args is None:
        import ssl as _ssl
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE
        connect_args = {"ssl": ssl_ctx}

    engine = create_async_engine(
        database_url,
        connect_args=connect_args,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    logger.info("database_initialized")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI DB dependency.
    NEVER auto-commits — endpoints must call db.commit() explicitly.
    Always rolls back on exception, always closes session.
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized.")

    session: AsyncSession = async_session_factory()
    try:
        yield session
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            await session.close()
        except Exception:
            pass
