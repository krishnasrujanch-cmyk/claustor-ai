"""
Claustor AI — Alert Celery Tasks
Scheduled tasks for daily alerts and maintenance.
"""

import asyncio
import structlog
from app.workers.celery_app import app as celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.workers.tasks.alert_tasks.run_daily_alerts", bind=True, max_retries=3)
def run_daily_alerts(self):
    """
    Run daily alert check for all orgs.
    Sends renewal + obligation emails via Resend.
    Scheduled: 9 AM IST daily.
    """
    async def _run():
        from app.infrastructure.database.session import async_session_factory
        from app.services.alert_service import AlertService

        async with async_session_factory() as db:
            service = AlertService(db)
            result = await service.run_daily_alerts()
            logger.info("daily_alerts_complete", **result)
            return result

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("daily_alerts_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60 * 5)  # retry in 5 min


@celery_app.task(name="app.workers.tasks.alert_tasks.reset_monthly_usage")
def reset_monthly_usage():
    """
    Reset monthly usage counters for all orgs.
    Scheduled: 1st of every month at midnight.
    """
    async def _run():
        from sqlalchemy import select, update
        from app.infrastructure.database.session import async_session_factory
        from app.domain.models import Organisation
        from datetime import datetime, timezone

        async with async_session_factory() as db:
            await db.execute(
                update(Organisation).values(
                    queries_used=0,
                    usage_reset_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()
            logger.info("monthly_usage_reset_complete")

    asyncio.run(_run())


@celery_app.task(name="app.workers.tasks.alert_tasks.cleanup_expired_guests")
def cleanup_expired_guests():
    """
    Deactivate expired guest users.
    Scheduled: 1 AM daily.
    """
    async def _run():
        from sqlalchemy import select, update
        from app.infrastructure.database.session import async_session_factory
        from app.domain.models import User
        from datetime import datetime, timezone

        async with async_session_factory() as db:
            result = await db.execute(
                select(User).where(
                    User.is_external == True,
                    User.is_active == True,
                    User.guest_expires_at < datetime.now(timezone.utc),
                )
            )
            expired = result.scalars().all()

            for user in expired:
                await db.execute(
                    update(User)
                    .where(User.id == user.id)
                    .values(is_active=False)
                )
                logger.info("guest_expired", user_id=str(user.id), email=user.email)

            await db.commit()
            logger.info("guest_cleanup_complete", deactivated=len(expired))

    asyncio.run(_run())
