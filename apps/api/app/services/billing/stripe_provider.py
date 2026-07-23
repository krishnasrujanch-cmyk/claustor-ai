"""
Claustor AI — Stripe Billing Provider
Activated when STRIPE_SECRET_KEY is set in .env
Handles: international payments (USD)
"""

import structlog

from app.services.billing.base import (
    BaseBillingProvider, BillingInterval, CustomerInfo,
    InvoiceInfo, SubscriptionInfo, SubscriptionStatus,
)

logger = structlog.get_logger(__name__)

# Stripe Price IDs — set these after creating products in Stripe dashboard
STRIPE_PRICES = {
    ("starter",      "monthly"): "price_starter_monthly",
    ("starter",      "annual"):  "price_starter_annual",
    ("professional", "monthly"): "price_pro_monthly",
    ("professional", "annual"):  "price_pro_annual",
    ("enterprise",   "monthly"): "price_enterprise_monthly",
}


class StripeBillingProvider(BaseBillingProvider):
    """
    Stripe billing provider.
    Activated when STRIPE_SECRET_KEY is set.
    Used for: international customers (USD billing)
    """

    def __init__(self, api_key: str, webhook_secret: str):
        try:
            import stripe
            stripe.api_key = api_key
            self.stripe = stripe
            self.webhook_secret = webhook_secret
            logger.info("stripe_provider_initialized")
        except ImportError:
            raise RuntimeError("stripe package not installed. Run: pip install stripe")

    def get_provider_name(self) -> str:
        return "stripe"

    async def create_customer(self, email, name, org_id, metadata=None) -> CustomerInfo:
        import asyncio
        loop = asyncio.get_event_loop()

        customer = await loop.run_in_executor(None, lambda: self.stripe.Customer.create(
            email=email,
            name=name,
            metadata={"org_id": org_id, **(metadata or {})},
        ))
        logger.info("stripe_customer_created", customer_id=customer.id)
        return CustomerInfo(
            provider_customer_id=customer.id,
            email=email,
            name=name,
            provider="stripe",
        )

    async def create_subscription(self, customer_id, plan, interval=BillingInterval.MONTHLY, trial_days=14) -> SubscriptionInfo:
        import asyncio
        from datetime import datetime, timezone

        price_key = (plan, interval.value)
        price_id = STRIPE_PRICES.get(price_key)
        if not price_id:
            raise ValueError(f"No Stripe price found for {plan}/{interval}")

        loop = asyncio.get_event_loop()
        sub = await loop.run_in_executor(None, lambda: self.stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            trial_period_days=trial_days if trial_days else None,
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        ))

        return SubscriptionInfo(
            provider_subscription_id=sub.id,
            provider_customer_id=customer_id,
            plan=plan,
            status=SubscriptionStatus(sub.status),
            interval=interval,
            amount=sub.items.data[0].price.unit_amount / 100,
            currency=sub.currency.upper(),
            current_period_start=datetime.fromtimestamp(sub.current_period_start, tz=timezone.utc),
            current_period_end=datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc),
            cancel_at_period_end=sub.cancel_at_period_end,
            trial_end=datetime.fromtimestamp(sub.trial_end, tz=timezone.utc) if sub.trial_end else None,
        )

    async def cancel_subscription(self, subscription_id, cancel_immediately=False) -> SubscriptionInfo:
        import asyncio
        from datetime import datetime, timezone
        loop = asyncio.get_event_loop()

        if cancel_immediately:
            sub = await loop.run_in_executor(None, lambda: self.stripe.Subscription.delete(subscription_id))
        else:
            sub = await loop.run_in_executor(None, lambda: self.stripe.Subscription.modify(
                subscription_id, cancel_at_period_end=True
            ))

        return SubscriptionInfo(
            provider_subscription_id=sub.id,
            provider_customer_id=sub.customer,
            plan="cancelled",
            status=SubscriptionStatus.CANCELLED,
            interval=BillingInterval.MONTHLY,
            amount=0, currency="USD",
            current_period_start=datetime.fromtimestamp(sub.current_period_start, tz=timezone.utc),
            current_period_end=datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc),
            cancel_at_period_end=sub.cancel_at_period_end,
        )

    async def get_subscription(self, subscription_id) -> SubscriptionInfo | None:
        import asyncio
        from datetime import datetime, timezone
        loop = asyncio.get_event_loop()

        try:
            sub = await loop.run_in_executor(None, lambda: self.stripe.Subscription.retrieve(subscription_id))
            return SubscriptionInfo(
                provider_subscription_id=sub.id,
                provider_customer_id=sub.customer,
                plan=sub.metadata.get("plan", "unknown"),
                status=SubscriptionStatus(sub.status),
                interval=BillingInterval.MONTHLY,
                amount=sub.items.data[0].price.unit_amount / 100,
                currency=sub.currency.upper(),
                current_period_start=datetime.fromtimestamp(sub.current_period_start, tz=timezone.utc),
                current_period_end=datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc),
                cancel_at_period_end=sub.cancel_at_period_end,
            )
        except Exception:
            return None

    async def get_invoices(self, customer_id, limit=10) -> list[InvoiceInfo]:
        import asyncio
        from datetime import datetime, timezone
        loop = asyncio.get_event_loop()

        invoices = await loop.run_in_executor(None, lambda: self.stripe.Invoice.list(
            customer=customer_id, limit=limit
        ))
        return [
            InvoiceInfo(
                provider_invoice_id=inv.id,
                amount=inv.amount_paid / 100,
                currency=inv.currency.upper(),
                status=inv.status,
                period_start=datetime.fromtimestamp(inv.period_start, tz=timezone.utc),
                period_end=datetime.fromtimestamp(inv.period_end, tz=timezone.utc),
                invoice_url=inv.hosted_invoice_url,
                invoice_pdf=inv.invoice_pdf,
            )
            for inv in invoices.data
        ]

    async def create_portal_session(self, customer_id, return_url) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        session = await loop.run_in_executor(None, lambda: self.stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        ))
        return session.url

    def verify_webhook(self, payload: bytes, sig_header: str) -> dict:
        """Verify Stripe webhook signature."""
        return self.stripe.Webhook.construct_event(
            payload, sig_header, self.webhook_secret
        )
