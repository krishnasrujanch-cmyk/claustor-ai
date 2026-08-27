"""
Claustor AI — Contract Processing Tasks
Direct async execution — NO subprocess.
PipelineSessionManager handles all long-running DB sessions.
Outer session used only for fast step1 reads (<5s).
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
    max_retries=2,
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

    logger.info("contract_task_received",
                contract_id=contract_id, plan=plan, queue=queue)

    async def _run():
        from app.agents.pipeline.contract_pipeline import ContractPipeline
        from app.infrastructure.database.session_manager import PipelineSessionManager
        from app.core.config import settings


        # Create session manager — handles all long-running DB ops
        mgr = PipelineSessionManager(settings.DATABASE_URL)
        await mgr.initialize()

        try:
            pipeline = ContractPipeline()

            # No outer session — pipeline uses session_manager for ALL DB ops
            # Each DB operation gets its own fresh NullPool connection
            await pipeline.process(
                contract_id=UUID(contract_id),
                org_id=UUID(org_id),
                file_hash=file_hash,
                db=None,
                session_manager=mgr,
            )
            logger.info("contract_processed",
                        contract_id=contract_id, plan=plan)

        except Exception as e:
            logger.error("contract_pipeline_failed",
                         contract_id=contract_id, error=str(e))
            raise
        finally:
            try:
                await mgr.dispose()
            except Exception:
                pass

    try:
        # Create fresh event loop for this thread (threads pool)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()
    except Exception as exc:
        logger.error("contract_task_failed",
                     contract_id=contract_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)
