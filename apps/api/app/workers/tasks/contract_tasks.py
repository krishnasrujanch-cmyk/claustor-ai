"""
Claustor AI — Contract Processing Celery Tasks
Async contract analysis via Celery workers.
"""

import asyncio
import structlog
from app.workers.celery_app import app as celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.contract_tasks.process_contract",
    bind=True,
    max_retries=2,
    soft_time_limit=300,  # 5 min timeout
)
def process_contract(self, contract_id: str, org_id: str, user_id: str, file_path: str):
    """
    Process a contract asynchronously.
    Called after upload — runs full AI pipeline.
    """
    async def _run():
        import uuid
        from app.infrastructure.database.session import async_session_factory
        from app.agents.pipeline.contract_pipeline import ContractPipeline

        async with async_session_factory() as db:
            pipeline = ContractPipeline()
            await pipeline.run(
                contract_id=uuid.UUID(contract_id),
                org_id=uuid.UUID(org_id),
                user_id=uuid.UUID(user_id),
                file_path=file_path,
                db=db,
            )

    try:
        asyncio.run(_run())
        logger.info("contract_processed", contract_id=contract_id)
    except Exception as exc:
        logger.error("contract_processing_failed", contract_id=contract_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)
