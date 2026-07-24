"""
Test configuration.
Each test gets a fresh DB engine to avoid connection conflicts.
"""
import ssl
import asyncio
import pytest
from app.core.config import settings


@pytest.fixture(autouse=True)
async def fresh_db():
    """Give each test its own DB engine — no shared state."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    import app.infrastructure.database.session as db_module

    ssl_ctx = ssl.create_default_context()
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"ssl": ssl_ctx},
        pool_size=2,
        max_overflow=2,
        pool_pre_ping=True,
    )
    db_module.async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    yield
    await engine.dispose()
