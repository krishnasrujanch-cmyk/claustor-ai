"""Add industry columns to DB."""
import asyncio, ssl, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def migrate():
    from app.core.config import settings
    ssl_ctx = ssl.create_default_context()
    engine  = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": ssl_ctx})
    async with engine.begin() as conn:
        for sql, label in [
            ("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS industry VARCHAR(50) DEFAULT 'general'", "organisations.industry"),
            ("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS industry VARCHAR(50) DEFAULT 'general'",     "contracts.industry"),
        ]:
            try:
                await conn.execute(text(sql))
                print(f"✅ {label} added")
            except Exception as e:
                print(f"  {label}: {e}")
    await engine.dispose()
    print("✅ Migration complete")

asyncio.run(migrate())
