"""
Claustor AI — Razorpay Billing Provider
Activated when RAZORPAY_KEY_ID is set in .env
Handles: Indian payments (INR), UPI, NetBanking, Cards
"""

import structlog

from app.services.billing.base import (
    BaseBillingProvider, BillingInterval, CustomerInfo,
    InvoiceInfo, SubscriptionInfo, SubscriptionStatus,
)

logger = structlog.get_logger(__name__)

# Razorpay Plan IDs — set after creating plans in Razorpay dashboard
RAZORPAY_PLANS = {
    ("starter",      "monthly"): "plan_starter_monthly",
    ("starter",      "annual"):  "plan_starter_annual",
    ("professional", "monthly"): "plan_pro_monthly",
    ("professional", "annual"):  "plan_pro_annual",
}

# INR amounts in paise (1 INR = 100 paise)
PLAN_AMOUNTS_PAISE = {
    "starter":      399900,   # ₹3,999
    "professional": 1649900,  # ₹16,499
}


class RazorpayBillingProvider(BaseBillingProvider):
    """
    Razorpay billing provider.
    Activated when RAZORPAY_KEY_ID is set.
    Used for: Indian customers (INR billing, UPI, NetBanking)
    """

    def __init__(self, key_id: str, key_secret: str, webhook_secret: str):
        try:
            import razorpay
            self.client = razorpay.Client(auth=(key_id, key_secret))
            self.webhook_secret = webhook_secret
            logger.info("razorpay_provider_initialized")
        except ImportError:
            raise RuntimeError("razorpay package not installed. Run: pip install razorpay")

    def get_provider_name(self) -> str:
        return "razorpay"

    async def create_customer(self, email, name, org_id, metadata=None) -> CustomerInfo:
        import asyncio
        loop = asyncio.get_event_loop()

        customer = await loop.run_in_executor(None, lambda: self.client.customer.create({
            "name": name,
            "email": email,
            "notes": {"org_id": org_id},
        }))
        logger.info("razorpay_customer_created", customer_id=customer["id"])
        return CustomerInfo(
            provider_customer_id=customer["id"],
            email=email,
            name=name,
            provider="razorpay",
        )

    async def create_subscription(self, customer_id, plan, interval=BillingInterval.MONTHLY, trial_days=14) -> SubscriptionInfo:
        import asyncio
        from datetime import datetime, timezone, timedelta
        loop = asyncio.get_event_loop()

        plan_key = (plan, interval.value)
        plan_id = RAZORPAY_PLANS.get(plan_key)
        if not plan_id:
            raise ValueError(f"No Razorpay plan found for {plan}/{interval}")

        sub = await loop.run_in_executor(None, lambda: self.client.subscription.create({
            "plan_id": plan_id,
            "customer_notify": 1,
            "total_count": 12 if interval == BillingInterval.MONTHLY else 1,
            "notes": {"customer_id": customer_id, "plan": plan},
        }))

        now = datetime.now(timezone.utc)
        return SubscriptionInfo(
            provider_subscription_id=sub["id"],
            provider_customer_id=customer_id,
            plan=plan,
            status=SubscriptionStatus.TRIALING if trial_days else SubscriptionStatus.ACTIVE,
            interval=interval,
            amount=PLAN_AMOUNTS_PAISE.get(plan, 0) / 100,
            currency="INR",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=False,
            trial_end=now + timedelta(days=trial_days) if trial_days else None,
        )

    async def cancel_subscription(self, subscription_id, cancel_immediately=False) -> SubscriptionInfo:
        import asyncio
        from datetime import datetime, timezone, timedelta
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(None, lambda: self.client.subscription.cancel(
            subscription_id,
            {"cancel_at_cycle_end": 0 if cancel_immediately else 1}
        ))

        now = datetime.now(timezone.utc)
        return SubscriptionInfo(
            provider_subscription_id=subscription_id,
            provider_customer_id="",
            plan="free",
            status=SubscriptionStatus.CANCELLED,
            interval=BillingInterval.MONTHLY,
            amount=0, currency="INR",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=not cancel_immediately,
        )

    async def get_subscription(self, subscription_id) -> SubscriptionInfo | None:
        import asyncio
        from datetime import datetime, timezone
        loop = asyncio.get_event_loop()
        try:
            sub = await loop.run_in_executor(None, lambda: self.client.subscription.fetch(subscription_id))
            now = datetime.now(timezone.utc)
            return SubscriptionInfo(
                provider_subscription_id=sub["id"],
                provider_customer_id=sub.get("customer_id", ""),
                plan=sub.get("notes", {}).get("plan", "unknown"),
                status=SubscriptionStatus.ACTIVE,
                interval=BillingInterval.MONTHLY,
                amount=sub.get("plan_amount", 0) / 100,
                currency="INR",
                current_period_start=now,
                current_period_end=datetime.fromtimestamp(sub.get("current_end", now.timestamp()), tz=timezone.utc),
                cancel_at_period_end=False,
            )
        except Exception:
            return None

    async def get_invoices(self, customer_id, limit=10) -> list[InvoiceInfo]:
        # Razorpay uses "payments" not "invoices"
        import asyncio
        from datetime import datetime, timezone
        loop = asyncio.get_event_loop()
        try:
            payments = await loop.run_in_executor(None, lambda: self.client.payment.all({
                "count": limit
            }))
            return [
                InvoiceInfo(
                    provider_invoice_id=p["id"],
                    amount=p["amount"] / 100,
                    currency=p["currency"],
                    status=p["status"],
                    period_start=datetime.fromtimestamp(p["created_at"], tz=timezone.utc),
                    period_end=datetime.fromtimestamp(p["created_at"], tz=timezone.utc),
                )
                for p in payments.get("items", [])
            ]
        except Exception:
            return []

    async def create_portal_session(self, customer_id, return_url) -> str:
        # Razorpay doesn't have a portal — redirect to billing page
        return f"{return_url}/billing"

    def verify_webhook(self, payload: str, signature: str) -> bool:
        """Verify Razorpay webhook signature."""
        import hmac
        import hashlib
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
