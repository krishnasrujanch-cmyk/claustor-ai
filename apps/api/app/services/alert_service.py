"""
Claustor AI — Alert Service
Sends renewal reminders and obligation due date alerts via Resend.
Called by Celery Beat scheduler daily at 9 AM.
"""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Contract, Obligation, Organisation, User

logger = structlog.get_logger(__name__)

# Alert thresholds (days before due date)
RENEWAL_ALERT_DAYS    = [120, 90, 60, 30, 14, 7]
OBLIGATION_ALERT_DAYS = [30, 14, 7, 1]


class AlertService:
    """Scans contracts + obligations and sends email alerts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_daily_alerts(self) -> dict:
        """
        Main alert runner — called by Celery Beat daily.
        Scans all active orgs and sends relevant alerts.
        """
        today = date.today()
        renewal_sent = 0
        obligation_sent = 0

        # Get all active orgs
        result = await self.db.execute(
            select(Organisation.id, Organisation.plan)
            .where(Organisation.is_active == True)
        )
        orgs = result.fetchall()

        for org in orgs:
            # Skip free plan — no alerts
            if org.plan == "free":
                continue

            r = await self._check_renewals(org.id, today)
            o = await self._check_obligations(org.id, today)
            renewal_sent += r
            obligation_sent += o

        logger.info(
            "daily_alerts_complete",
            renewal_alerts=renewal_sent,
            obligation_alerts=obligation_sent,
        )
        return {"renewal_alerts": renewal_sent, "obligation_alerts": obligation_sent}

    async def _check_renewals(self, org_id: UUID, today: date) -> int:
        """Check contracts expiring soon and send renewal alerts."""
        sent = 0

        for days_ahead in RENEWAL_ALERT_DAYS:
            target_date = today + timedelta(days=days_ahead)

            result = await self.db.execute(
                select(Contract).where(
                    Contract.org_id == org_id,
                    Contract.is_active == True,
                    Contract.expiry_date == target_date,
                    Contract.status == "analyzed",
                )
            )
            contracts = result.scalars().all()

            for contract in contracts:
                await self._send_renewal_alert(contract, days_ahead)
                sent += 1

        return sent

    async def _check_obligations(self, org_id: UUID, today: date) -> int:
        """Check obligations due soon and send alerts."""
        sent = 0

        for days_ahead in OBLIGATION_ALERT_DAYS:
            target_date = today + timedelta(days=days_ahead)

            result = await self.db.execute(
                select(Obligation).where(
                    Obligation.org_id == org_id,
                    Obligation.due_date == target_date,
                    Obligation.status == "pending",
                )
            )
            obligations = result.scalars().all()

            for obligation in obligations:
                await self._send_obligation_alert(obligation, days_ahead)
                sent += 1

        return sent

    async def _get_org_admins(self, org_id: UUID) -> list[str]:
        """Get email addresses of org admins for alerts."""
        result = await self.db.execute(
            select(User.email).where(
                User.org_id == org_id,
                User.role.in_(["super_admin", "dept_admin", "contract_manager"]),
                User.is_active == True,
            )
        )
        return [row.email for row in result.fetchall()]

    async def _send_renewal_alert(self, contract: Contract, days_ahead: int) -> None:
        """Send contract renewal alert email."""
        try:
            from app.core.config import settings
            if not settings.RESEND_API_KEY:
                logger.info("renewal_alert_skipped", reason="no_resend_key",
                           contract_id=str(contract.id), days=days_ahead)
                return

            admin_emails = await self._get_org_admins(contract.org_id)
            if not admin_emails:
                return

            import resend
            resend.api_key = settings.RESEND_API_KEY

            urgency = "🚨 URGENT" if days_ahead <= 14 else "⚠️ Action Required" if days_ahead <= 30 else "📅 Reminder"

            resend.Emails.send({
                "from": f"Claustor AI <{settings.RESEND_FROM}>",
                "to": admin_emails,
                "subject": f"{urgency}: {contract.title} expires in {days_ahead} days",
                "html": f"""
                <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:32px;">
                  <div style="background:#5B4BFF;color:white;padding:20px 24px;border-radius:12px 12px 0 0;">
                    <h2 style="margin:0;font-size:18px;">Contract Renewal Alert</h2>
                  </div>
                  <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-top:none;padding:24px;border-radius:0 0 12px 12px;">
                    <h3 style="color:#111827;margin-top:0;">{contract.title}</h3>
                    <p style="color:#374151;">This contract expires in <strong>{days_ahead} days</strong> on <strong>{contract.expiry_date}</strong>.</p>
                    {"<p style='color:#DC2626;font-weight:600;'>⚠️ Auto-renewal notice required " + str(contract.renewal_notice_days) + " days before expiry.</p>" if contract.auto_renewal and contract.renewal_notice_days else ""}
                    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                      <tr><td style="padding:8px 0;color:#6B7280;font-size:13px;">Counterparty</td><td style="padding:8px 0;color:#111827;font-weight:600;font-size:13px;">{contract.counterparty or "—"}</td></tr>
                      <tr><td style="padding:8px 0;color:#6B7280;font-size:13px;">Contract value</td><td style="padding:8px 0;color:#111827;font-weight:600;font-size:13px;">{contract.contract_currency or "USD"} {contract.contract_value:,.0f if contract.contract_value else "—"}</td></tr>
                      <tr><td style="padding:8px 0;color:#6B7280;font-size:13px;">Auto-renewal</td><td style="padding:8px 0;color:#111827;font-weight:600;font-size:13px;">{"Yes" if contract.auto_renewal else "No"}</td></tr>
                    </table>
                    <a href="https://claustor.com/dashboard/contracts/{contract.id}" style="display:inline-block;background:#5B4BFF;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
                      Review contract →
                    </a>
                    <p style="color:#9CA3AF;font-size:12px;margin-top:24px;">Claustor AI · claustor.com · Unsubscribe</p>
                  </div>
                </div>
                """,
            })

            logger.info("renewal_alert_sent",
                       contract_id=str(contract.id), days=days_ahead, recipients=len(admin_emails))

        except Exception as e:
            logger.error("renewal_alert_failed", error=str(e), contract_id=str(contract.id))

    async def _send_obligation_alert(self, obligation: Obligation, days_ahead: int) -> None:
        """Send obligation due date alert email."""
        try:
            from app.core.config import settings
            if not settings.RESEND_API_KEY:
                return

            admin_emails = await self._get_org_admins(obligation.org_id)
            if not admin_emails:
                return

            import resend
            resend.api_key = settings.RESEND_API_KEY

            urgency = "🚨 DUE TOMORROW" if days_ahead == 1 else "⚠️ DUE SOON" if days_ahead <= 7 else "📅 Upcoming"

            resend.Emails.send({
                "from": f"Claustor AI <{settings.RESEND_FROM}>",
                "to": admin_emails,
                "subject": f"{urgency}: {obligation.title} due in {days_ahead} day{'s' if days_ahead>1 else ''}",
                "html": f"""
                <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:32px;">
                  <div style="background:#F59E0B;color:white;padding:20px 24px;border-radius:12px 12px 0 0;">
                    <h2 style="margin:0;font-size:18px;">Obligation Due {("Tomorrow" if days_ahead==1 else f"in {days_ahead} days")}</h2>
                  </div>
                  <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-top:none;padding:24px;border-radius:0 0 12px 12px;">
                    <h3 style="color:#111827;margin-top:0;">{obligation.title}</h3>
                    <p style="color:#374151;">{obligation.description or ""}</p>
                    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                      <tr><td style="padding:8px 0;color:#6B7280;font-size:13px;">Type</td><td style="padding:8px 0;color:#111827;font-weight:600;font-size:13px;">{obligation.obligation_type}</td></tr>
                      <tr><td style="padding:8px 0;color:#6B7280;font-size:13px;">Party</td><td style="padding:8px 0;color:#111827;font-weight:600;font-size:13px;">{obligation.party or "—"}</td></tr>
                      <tr><td style="padding:8px 0;color:#6B7280;font-size:13px;">Due date</td><td style="padding:8px 0;color:#DC2626;font-weight:700;font-size:13px;">{obligation.due_date}</td></tr>
                      {f'<tr><td style="padding:8px 0;color:#6B7280;font-size:13px;">Amount</td><td style="padding:8px 0;color:#111827;font-weight:600;font-size:13px;">{obligation.currency or "USD"} {obligation.amount:,.0f}</td></tr>' if obligation.amount else ""}
                    </table>
                    <a href="https://claustor.com/dashboard/obligations" style="display:inline-block;background:#F59E0B;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
                      View obligation →
                    </a>
                  </div>
                </div>
                """,
            })

            logger.info("obligation_alert_sent",
                       obligation_id=str(obligation.id), days=days_ahead)

        except Exception as e:
            logger.error("obligation_alert_failed", error=str(e), obligation_id=str(obligation.id))
