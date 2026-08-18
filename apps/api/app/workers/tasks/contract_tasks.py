"""
Claustor AI — Contract Processing Tasks
Direct async execution — NO subprocess.
Uses existing session factory to avoid connection issues.
"""
from __future__ import annotations
import asyncio
import structlog
from uuid import UUID

from app.workers.celery_app import app as celery_app

PLAN_QUEUES = {
    "free":         "free_queue",
    "starter":      "starter_queue",
    "professional": "pro_queue",
    "enterprise":   "enterprise_queue",
}

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.contract_tasks.process_contract",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=1800,
    time_limit=2100,
)
def process_contract(
    self,
    contract_id: str,
    org_id: str,
    file_hash: str,
    plan: str = "starter",
    queue: str = "starter_queue",
    file_path: str = "",
    user_id: str = "",
    **kwargs,
):
    # Support both file_hash and file_path parameter names
    if not file_hash and file_path:
        file_hash = file_path
    """
    Process contract via direct async execution.
    No subprocess — uses shared session factory.
    Supports 100s of concurrent documents via Celery concurrency.
    """
    logger.info("contract_task_received",
                contract_id=contract_id, plan=plan, queue=queue)

    async def _run():
        from app.infrastructure.database.session import (
            async_session_factory, init_db
        )
        from app.agents.pipeline.contract_pipeline import ContractPipeline
        from app.core.config import settings

        # Initialize DB if not already done (first task in worker)
        if async_session_factory is None:
            await init_db(settings.DATABASE_URL)

        async with async_session_factory() as db:
            try:
                pipeline = ContractPipeline()
                await pipeline.process(
                    contract_id=UUID(contract_id),
                    org_id=UUID(org_id),
                    file_hash=file_hash,
                    db=db,
                )
                await db.commit()
                logger.info("contract_processed",
                            contract_id=contract_id, plan=plan)
            except Exception as e:
                try:
                    await db.rollback()
                except Exception:
                    pass
                logger.error("contract_pipeline_failed",
                             contract_id=contract_id, error=str(e))
                raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("contract_task_failed",
                     contract_id=contract_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)
