"""Claustor AI — Contract Processing Celery Tasks."""

import os
import subprocess
import sys
import structlog
from app.workers.celery_app import app as celery_app

logger = structlog.get_logger(__name__)

PLAN_QUEUES = {
    "free":         "free_queue",
    "starter":      "starter_queue",
    "professional": "pro_queue",
    "enterprise":   "enterprise_queue",
}


@celery_app.task(
    name="app.workers.tasks.contract_tasks.process_contract",
    bind=True,
    max_retries=2,
    soft_time_limit=600,
    queue="starter_queue",
)
def process_contract(self, contract_id: str, org_id: str, user_id: str, file_path: str, plan: str = "starter"):
    """Process contract in isolated subprocess."""
    logger.info("contract_task_received",
                contract_id=contract_id, plan=plan,
                queue=PLAN_QUEUES.get(plan, "starter_queue"))

    api_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )))

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{api_dir}:{existing}" if existing else api_dir

    script = f"""
import asyncio, ssl, os, uuid
os.makedirs(os.path.expanduser("~/claustor-uploads"), exist_ok=True)

async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.core.config import settings
    from app.agents.pipeline.contract_pipeline import ContractPipeline

    ssl_ctx = ssl.create_default_context()
    engine = create_async_engine(settings.DATABASE_URL, connect_args={{"ssl": ssl_ctx}}, pool_size=2, max_overflow=0)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as db:
            pipeline = ContractPipeline()
            await pipeline.process(
                contract_id=uuid.UUID("{contract_id}"),
                org_id=uuid.UUID("{org_id}"),
                file_hash="{file_path}",
                db=db,
            )
        print("SUCCESS")
    finally:
        await engine.dispose()

asyncio.run(main())
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True,
            timeout=540, env=env, cwd=api_dir,
        )
        if result.returncode != 0:
            error = result.stderr[-2000:] if result.stderr else "Unknown"
            logger.error("contract_subprocess_failed", contract_id=contract_id, error=error)
            raise RuntimeError(error)
        logger.info("contract_processed", contract_id=contract_id, plan=plan)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout: {contract_id}")
    except Exception as exc:
        logger.error("contract_task_failed", contract_id=contract_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)
