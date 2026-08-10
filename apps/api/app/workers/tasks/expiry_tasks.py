"""
Claustor AI — Plan Expiry & Grace Period Tasks
Runs daily via Celery Beat.

Flow:
  next_billing_date passes → grace_period starts (7 days)
  grace_period_end passes  → downgrade to free
  reminder_sent_days tracks which emails already sent
"""

import asyncio
import structlog
from datetime import datetime, timezone, timedelta
from celery import shared_task

logger = structlog.get_logger(__name__)

GRACE_PERIOD_DAYS = 7

REMINDER_SCHEDULE = [15, 7, 3, 1]  # days before expiry

EMAIL_TEMPLATES = {
    "reminder_15": {
        "subject": "Your Claustor AI plan renews in 15 days",
        "body":    "Your {plan} plan renews on {date}. Please ensure your payment is ready.",
    },
    "reminder_7": {
        "subject": "Action needed: Claustor AI plan expires in 7 days",
        "body":    "Your {plan} plan expires on {date}. Renew now to avoid interruption.",
    },
    "reminder_3": {
        "subject": "3 days left — Claustor AI plan expiring soon",
        "body":    "Your {plan} plan expires in 3 days on {date}. Renew now.",
    },
    "reminder_1": {
        "subject": "Last reminder: Claustor AI plan expires tomorrow",
        "body":    "Your {plan} plan expires tomorrow. Renew now to keep full access.",
    },
    "grace_started": {
        "subject": "Payment overdue — grace period started",
        "body":    "Your {plan} plan payment is overdue. You have 7 days of full access remaining. Renew now.",
    },
    "grace_reminder_3": {
        "subject": "4 days left in grace period — Claustor AI",
        "body":    "Your account will be downgraded to Free in 4 days unless payment is received.",
    },
    "downgraded": {
        "subject": "Your Claustor AI account has been downgraded",
        "body":    "Your {plan} plan has expired and your account has been downgraded to Free. Your data is preserved. Upgrade anytime.",
    },
}


async def _send_email(email: str, subject: str, body: str,
                      org_name: str = "", event_type: str = "subscription_expiring",
                      days: int = 0, plan: str = "") -> bool:
    """Send notification via centralized notification service."""
    from app.services.notifications import send_notification, NotificationEvent, NotificationPayload
    event_map = {
        "subscription_expiring": NotificationEvent.SUBSCRIPTION_EXPIRING,
        "trial_ending":          NotificationEvent.TRIAL_ENDING,
        "plan_downgraded":       NotificationEvent.PLAN_DOWNGRADED,
        "payment_failed":        NotificationEvent.PAYMENT_FAILED,
        "contract_expiring":     NotificationEvent.CONTRACT_EXPIRING,
        "renewal_required":      NotificationEvent.RENEWAL_REQUIRED,
        "obligation_due":        NotificationEvent.OBLIGATION_DUE,
    }
    event = event_map.get(event_type, NotificationEvent.SUBSCRIPTION_EXPIRING)
    return await send_notification(NotificationPayload(
        event=event,
        recipient_email=email,
        recipient_name=email.split("@")[0].title(),
        org_name=org_name,
        action_url="https://claustor.ai/dashboard/admin/billing",
        extra={"days": days, "plan": plan, "body": body},
    ))


async def _run_expiry_check():
    """Core expiry check logic — runs daily."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text, update
    from app.core.config import settings
    from app.domain.models.models import Organisation

    engine = create_async_engine(settings.DATABASE_URL)
    now = datetime.now(timezone.utc)

    async with AsyncSession(engine) as db:
        # ── 1. Send renewal reminders ────────────────────────────
        r = await db.execute(text("""
            SELECT o.id, o.name, o.plan, o.next_billing_date,
                   o.reminder_sent_days, u.email
            FROM organisations o
            JOIN users u ON u.org_id = o.id AND u.role = 'super_admin'
            WHERE o.plan != 'free'
              AND o.payment_status = 'active'
              AND o.next_billing_date IS NOT NULL
              AND o.next_billing_date > :now
            ORDER BY o.next_billing_date ASC
        """), {"now": now})
        orgs = r.fetchall()

        for org in orgs:
            org_id, name, plan, next_date, sent_days, email = org
            if not next_date:
                continue

            days_left = (next_date - now).days
            sent = sent_days or []

            for remind_day in REMINDER_SCHEDULE:
                if days_left <= remind_day and remind_day not in sent:
                    tmpl = EMAIL_TEMPLATES.get(f"reminder_{remind_day}", {})
                    subject = tmpl.get("subject","")
                    body    = tmpl.get("body","").format(
                        plan=plan.title(),
                        date=next_date.strftime("%d %b %Y"),
                    )
                    ok = await _send_email(email, subject, body, name)
                    if ok:
                        sent.append(remind_day)
                        await db.execute(text("""
                            UPDATE organisations
                            SET reminder_sent_days = :sent
                            WHERE id = :id
                        """), {"sent": sent, "id": str(org_id)})
                        logger.info("reminder_sent",
                            org_id=str(org_id), days_left=days_left,
                            remind_day=remind_day)

        await db.commit()

        # ── 2. Start grace period for expired plans ──────────────
        r2 = await db.execute(text("""
            SELECT o.id, o.name, o.plan, o.next_billing_date, u.email
            FROM organisations o
            JOIN users u ON u.org_id = o.id AND u.role = 'super_admin'
            WHERE o.plan != 'free'
              AND o.payment_status = 'active'
              AND o.next_billing_date IS NOT NULL
              AND o.next_billing_date <= :now
        """), {"now": now})
        expired = r2.fetchall()

        for org in expired:
            org_id, name, plan, next_date, email = org
            grace_end = now + timedelta(days=GRACE_PERIOD_DAYS)

            await db.execute(text("""
                UPDATE organisations
                SET payment_status   = 'grace_period',
                    grace_period_end = :grace_end,
                    reminder_sent_days = ARRAY[]::integer[]
                WHERE id = :id
            """), {"grace_end": grace_end, "id": str(org_id)})

            tmpl = EMAIL_TEMPLATES["grace_started"]
            await _send_email(
                email,
                tmpl["subject"],
                tmpl["body"].format(plan=plan.title(), date=""),
                name,
            )
            logger.info("grace_period_started",
                org_id=str(org_id), grace_end=grace_end.isoformat())

        await db.commit()

        # ── 3. Grace period reminder (day +3) ───────────────────
        r3 = await db.execute(text("""
            SELECT o.id, o.name, o.plan, o.grace_period_end,
                   o.reminder_sent_days, u.email
            FROM organisations o
            JOIN users u ON u.org_id = o.id AND u.role = 'super_admin'
            WHERE o.payment_status = 'grace_period'
              AND o.grace_period_end IS NOT NULL
        """), {})
        grace_orgs = r3.fetchall()

        for org in grace_orgs:
            org_id, name, plan, grace_end, sent_days, email = org
            days_left = (grace_end - now).days
            sent      = sent_days or []

            if days_left <= 4 and "grace_3" not in sent:
                tmpl = EMAIL_TEMPLATES["grace_reminder_3"]
                ok   = await _send_email(email, tmpl["subject"], tmpl["body"], name)
                if ok:
                    sent.append("grace_3")
                    await db.execute(text("""
                        UPDATE organisations
                        SET reminder_sent_days = :sent
                        WHERE id = :id
                    """), {"sent": sent, "id": str(org_id)})

        await db.commit()

        # ── 4. Downgrade expired grace periods ───────────────────
        r4 = await db.execute(text("""
            SELECT o.id, o.name, o.plan, u.email
            FROM organisations o
            JOIN users u ON u.org_id = o.id AND u.role = 'super_admin'
            WHERE o.payment_status = 'grace_period'
              AND o.grace_period_end IS NOT NULL
              AND o.grace_period_end <= :now
        """), {"now": now})
        to_downgrade = r4.fetchall()

        for org in to_downgrade:
            org_id, name, plan, email = org

            await db.execute(text("""
                UPDATE organisations
                SET plan           = 'free',
                    payment_status = 'expired',
                    addon_enabled  = FALSE,
                    next_billing_date = NULL,
                    grace_period_end  = NULL,
                    reminder_sent_days = ARRAY[]::integer[]
                WHERE id = :id
            """), {"id": str(org_id)})

            tmpl = EMAIL_TEMPLATES["downgraded"]
            await _send_email(
                email,
                tmpl["subject"],
                tmpl["body"].format(plan=plan.title(), date=""),
                name,
            )
            logger.info("plan_downgraded_to_free",
                org_id=str(org_id), previous_plan=plan)

        await db.commit()
        await engine.dispose()

        stats = {
            "reminders_checked": len(orgs),
            "grace_started":     len(expired),
            "downgraded":        len(to_downgrade),
        }
        logger.info("expiry_check_complete", **stats)
        return stats


@shared_task(name="run_expiry_check", bind=True, max_retries=3)
def run_expiry_check(self):
    """Daily plan expiry check — reminders, grace period, downgrade."""
    try:
        return asyncio.run(_run_expiry_check())
    except Exception as exc:
        logger.error("expiry_check_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=3600)  # retry in 1 hour
