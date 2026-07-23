"""
Claustor AI — Billing Service
Central billing orchestration.
Auto-selects provider: Stripe (intl) → Razorpay (India) → Mock (dev)
Handles: usage tracking, plan enforcement, subscription management.
"""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.models import Organisation
from app.services.billing.base import BaseBillingProvider, BillingInterval

logger = structlog.get_logger(__name__)

# Plan definitions
PLANS = {
    "free": {
        "users": 1, "contracts": 5, "queries": 100,
        "storage_mb": 100, "extra_users": 0,
        "features": ["basic_extraction"],
    },
    "starter": {
        "users": 10, "contracts": 100, "queries": 5000,
        "storage_mb": 10240, "extra_users": 10,
        "features": ["basic_extraction", "ocr", "tables", "alerts"],
    },
    "professional": {
        "users": 50, "contracts": 1000, "queries": 50000,
        "storage_mb": 102400, "extra_users": 50,
        "features": ["basic_extraction", "ocr", "tables", "vision",
                     "api_access", "webhooks", "comparison", "playbook"],
    },
    "enterprise": {
        "users": -1, "contracts": -1, "queries": -1,
        "storage_mb": -1, "extra_users": -1,
        "features": ["all"],
    },
}

# Extra user pricing (per user per month)
EXTRA_USER_PRICE = {
    "starter":      299,   # ₹299/user/month
    "professional": 399,   # ₹399/user/month
}


def get_billing_provider() -> BaseBillingProvider:
    """
    Auto-select billing provider based on config.
    Priority: Stripe → Razorpay → Mock

    To activate Stripe: set STRIPE_SECRET_KEY in .env
    To activate Razorpay: set RAZORPAY_KEY_ID in .env
    Otherwise: Mock provider used (dev mode)
    """
    if settings.STRIPE_SECRET_KEY:
        from app.services.billing.stripe_provider import StripeBillingProvider
        logger.info("billing_provider", provider="stripe")
        return StripeBillingProvider(
            api_key=settings.STRIPE_SECRET_KEY,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
        )

    if getattr(settings, "RAZORPAY_KEY_ID", None):
        from app.services.billing.razorpay_provider import RazorpayBillingProvider
        logger.info("billing_provider", provider="razorpay")
        return RazorpayBillingProvider(
            key_id=settings.RAZORPAY_KEY_ID,
            key_secret=settings.RAZORPAY_KEY_SECRET,
            webhook_secret=settings.RAZORPAY_WEBHOOK_SECRET,
        )

    logger.info("billing_provider", provider="mock", note="Add STRIPE or RAZORPAY keys to activate real billing")
    from app.services.billing.mock_provider import MockBillingProvider
    return MockBillingProvider()


class UsageLimitError(Exception):
    """Raised when org exceeds plan limits."""
    def __init__(self, resource: str, current: int, limit: int, plan: str):
        self.resource = resource
        self.current = current
        self.limit = limit
        self.plan = plan
        super().__init__(
            f"Plan limit reached: {resource} ({current}/{limit}) on {plan} plan. "
            f"Please upgrade to continue."
        )


class BillingService:
    """
    Central billing service.
    All billing operations go through here.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider: BaseBillingProvider = get_billing_provider()

    # ── Usage Tracking ─────────────────────────────────────

    async def check_and_increment_contracts(
        self, org_id: UUID, plan: str
    ) -> None:
        """Check contract limit and increment usage counter."""
        limits = PLANS.get(plan, PLANS["free"])
        max_contracts = limits["contracts"]

        result = await self.db.execute(
            select(Organisation.contracts_used, Organisation.max_contracts)
            .where(Organisation.id == org_id)
        )
        row = result.first()
        if not row:
            return

        current = row.contracts_used or 0
        limit = row.max_contracts or max_contracts

        if limit != -1 and current >= limit:
            raise UsageLimitError("contracts", current, limit, plan)

        # Increment
        await self.db.execute(
            update(Organisation)
            .where(Organisation.id == org_id)
            .values(contracts_used=Organisation.contracts_used + 1)
        )
        await self.db.commit()

    async def check_and_increment_queries(
        self, org_id: UUID, plan: str
    ) -> None:
        """Check query limit and increment usage counter."""
        limits = PLANS.get(plan, PLANS["free"])
        max_queries = limits["queries"]

        if max_queries == -1:  # unlimited
            return

        result = await self.db.execute(
            select(Organisation.queries_used, Organisation.max_queries_mo)
            .where(Organisation.id == org_id)
        )
        row = result.first()
        if not row:
            return

        current = row.queries_used or 0
        limit = row.max_queries_mo or max_queries

        if current >= limit:
            raise UsageLimitError("queries", current, limit, plan)

        await self.db.execute(
            update(Organisation)
            .where(Organisation.id == org_id)
            .values(queries_used=Organisation.queries_used + 1)
        )
        await self.db.commit()

    async def get_usage(self, org_id: UUID) -> dict:
        """Get current usage stats for an org."""
        result = await self.db.execute(
            select(
                Organisation.plan,
                Organisation.contracts_used,
                Organisation.queries_used,
                Organisation.storage_used_mb,
                Organisation.max_contracts,
                Organisation.max_queries_mo,
                Organisation.max_users,
                Organisation.max_storage_mb,
                Organisation.usage_reset_at,
            ).where(Organisation.id == org_id)
        )
        row = result.first()
        if not row:
            return {}

        plan_limits = PLANS.get(row.plan, PLANS["free"])

        # Get actual contract count for accurate display
        from sqlalchemy import func
        from app.domain.models import Contract
        contract_count_result = await self.db.execute(
            select(func.count(Contract.id)).where(
                Contract.org_id == org_id,
                Contract.is_active == True,
            )
        )
        actual_contract_count = contract_count_result.scalar() or 0

        return {
            "plan": row.plan,
            "billing_provider": self.provider.get_provider_name(),
            "usage": {
                "contracts": {
                    "used": actual_contract_count,
                    "limit": row.max_contracts or plan_limits["contracts"],
                    "pct": round(actual_contract_count / max(row.max_contracts or 1, 1) * 100, 1),
                },
                "queries": {
                    "used": row.queries_used or 0,
                    "limit": row.max_queries_mo or plan_limits["queries"],
                    "pct": round((row.queries_used or 0) / max(row.max_queries_mo or 1, 1) * 100, 1),
                },
                "storage_mb": {
                    "used": round(row.storage_used_mb or 0, 2),
                    "limit": row.max_storage_mb or plan_limits["storage_mb"],
                },
            },
            "reset_at": row.usage_reset_at.isoformat() if row.usage_reset_at else None,
            "features": plan_limits.get("features", []),
        }

    async def reset_monthly_usage(self, org_id: UUID) -> None:
        """Reset monthly usage counters. Called by Celery Beat on 1st of month."""
        await self.db.execute(
            update(Organisation)
            .where(Organisation.id == org_id)
            .values(
                contracts_used=0,
                queries_used=0,
                usage_reset_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
        logger.info("usage_reset", org_id=str(org_id))

    # ── Subscription Management ────────────────────────────

    async def create_subscription(
        self,
        org_id: UUID,
        plan: str,
        email: str,
        org_name: str,
        interval: BillingInterval = BillingInterval.MONTHLY,
    ) -> dict:
        """Create customer + subscription for an org."""

        # Create customer in billing provider
        customer = await self.provider.create_customer(
            email=email,
            name=org_name,
            org_id=str(org_id),
        )

        # Create subscription
        subscription = await self.provider.create_subscription(
            customer_id=customer.provider_customer_id,
            plan=plan,
            interval=interval,
            trial_days=14,
        )

        # Update org with billing info
        plan_limits = PLANS.get(plan, PLANS["free"])
        await self.db.execute(
            update(Organisation)
            .where(Organisation.id == org_id)
            .values(
                plan=plan,
                stripe_customer_id=customer.provider_customer_id,
                stripe_subscription_id=subscription.provider_subscription_id,
                max_contracts=plan_limits["contracts"],
                max_queries_mo=plan_limits["queries"],
                max_users=plan_limits["users"],
                max_storage_mb=plan_limits["storage_mb"],
                plan_started_at=datetime.now(timezone.utc),
                plan_expires_at=subscription.current_period_end,
            )
        )
        await self.db.commit()

        logger.info(
            "subscription_created",
            org_id=str(org_id),
            plan=plan,
            provider=self.provider.get_provider_name(),
            subscription_id=subscription.provider_subscription_id,
        )

        return {
            "customer_id": customer.provider_customer_id,
            "subscription_id": subscription.provider_subscription_id,
            "plan": plan,
            "status": subscription.status.value,
            "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
            "period_end": subscription.current_period_end.isoformat(),
            "provider": self.provider.get_provider_name(),
        }

    async def cancel_subscription(
        self,
        org_id: UUID,
        cancel_immediately: bool = False,
    ) -> dict:
        """Cancel subscription and downgrade to free."""
        result = await self.db.execute(
            select(Organisation.stripe_subscription_id)
            .where(Organisation.id == org_id)
        )
        row = result.first()
        if not row or not row.stripe_subscription_id:
            raise ValueError("No active subscription found")

        sub = await self.provider.cancel_subscription(
            subscription_id=row.stripe_subscription_id,
            cancel_immediately=cancel_immediately,
        )

        if cancel_immediately:
            free_limits = PLANS["free"]
            await self.db.execute(
                update(Organisation)
                .where(Organisation.id == org_id)
                .values(
                    plan="free",
                    max_contracts=free_limits["contracts"],
                    max_queries_mo=free_limits["queries"],
                    max_users=free_limits["users"],
                )
            )
            await self.db.commit()

        logger.info("subscription_cancelled", org_id=str(org_id))
        return {"status": "cancelled", "cancel_at_period_end": sub.cancel_at_period_end}

    async def get_invoices(self, org_id: UUID) -> list[dict]:
        """Get invoice history for an org."""
        result = await self.db.execute(
            select(Organisation.stripe_customer_id)
            .where(Organisation.id == org_id)
        )
        row = result.first()
        if not row or not row.stripe_customer_id:
            return []

        invoices = await self.provider.get_invoices(row.stripe_customer_id)
        return [
            {
                "id": inv.provider_invoice_id,
                "amount": inv.amount,
                "currency": inv.currency,
                "status": inv.status,
                "period_start": inv.period_start.isoformat(),
                "period_end": inv.period_end.isoformat(),
                "invoice_url": inv.invoice_url,
                "invoice_pdf": inv.invoice_pdf,
            }
            for inv in invoices
        ]
