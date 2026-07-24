"""
Claustor AI — Contract Processing Celery Tasks
Async contract analysis via Celery workers.
"""

import asyncio
import structlog

from app.workers.celery_app import app as celery_app

logger = structlog.get_logger(__name__)


async def _init_db():
    """Initialize DB session factory if not already done."""
    from app.infrastructure.database.session import async_session_factory, init_db
    if async_session_factory is None:
        import ssl
        from app.core.config import settings
        ssl_ctx = ssl.create_default_context()
        await init_db(settings.DATABASE_URL, connect_args={"ssl": ssl_ctx})


@celery_app.task(
    name="app.workers.tasks.contract_tasks.process_contract",
    bind=True,
    max_retries=2,
    soft_time_limit=300,
)
def process_contract(self, contract_id: str, org_id: str, user_id: str, file_path: str):
    """
    Process a contract asynchronously via Celery.
    Initializes DB in worker process before running pipeline.
    """
    async def _run():
        import uuid
        # Initialize DB in this worker process
        await _init_db()

        from app.infrastructure.database.session import async_session_factory
        from app.agents.pipeline.contract_pipeline import ContractPipeline

        async with async_session_factory() as db:
            pipeline = ContractPipeline()
            await pipeline.process(
                contract_id=uuid.UUID(contract_id),
                org_id=uuid.UUID(org_id),
                file_hash=file_path,  # pipeline uses file_path stored in DB
                db=db,
            )

    try:
        asyncio.run(_run())
        logger.info("contract_processed", contract_id=contract_id)
    except Exception as exc:
        logger.error("contract_processing_failed",
                     contract_id=contract_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)
