"""
Claustor AI — Celery Tasks
Async contract processing tasks.
"""
import structlog

logger = structlog.get_logger(__name__)

try:
    from celery import Celery
    from app.core.config import settings

    broker_url = settings.RABBITMQ_URL or settings.REDIS_URL
    celery_app = Celery("claustor", broker=broker_url)

    @celery_app.task(name="process_contract", bind=True, max_retries=3)
    def process_contract(self, contract_id: str, org_id: str, file_hash: str):
        """Process contract async via Celery worker."""
        import asyncio
        from uuid import UUID

        async def _run():
            from app.infrastructure.database.session import async_session_factory, init_db
            from app.agents.pipeline.contract_pipeline import ContractPipeline

            if async_session_factory is None:
                await init_db()

            async with async_session_factory() as db:
                pipeline = ContractPipeline()
                await pipeline.process(
                    contract_id=UUID(contract_id),
                    org_id=UUID(org_id),
                    file_hash=file_hash,
                    db=db,
                )

        asyncio.run(_run())

except Exception as e:
    logger.warning("celery_not_available", error=str(e))

    class _FakeTask:
        def delay(self, *args, **kwargs):
            raise RuntimeError("Celery not available")

    process_contract = _FakeTask()
