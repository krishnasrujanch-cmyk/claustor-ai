"""
Claustor AI — Mock Billing Provider
Works without any API keys. Used in development.
Auto-activated when STRIPE_SECRET_KEY and RAZORPAY_KEY_ID are empty.
Simulates all billing operations with realistic responses.
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog

from app.services.billing.base import (
    BaseBillingProvider, BillingInterval, CustomerInfo,
    InvoiceInfo, SubscriptionInfo, SubscriptionStatus,
)

logger = structlog.get_logger(__name__)

# Mock plan pricing (INR)
MOCK_PLANS = {
    "free":         {"amount": 0,     "currency": "INR"},
    "starter":      {"amount": 3999,  "currency": "INR"},
    "professional": {"amount": 16499, "currency": "INR"},
    "enterprise":   {"amount": 150000,"currency": "INR"},
}


class MockBillingProvider(BaseBillingProvider):
    """
    Mock billing provider for development.
    All operations succeed and return realistic data.
    No API calls made — works offline.
    """

    def get_provider_name(self) -> str:
        return "mock"

    async def create_customer(
        self,
        email: str,
        name: str,
        org_id: str,
        metadata: dict | None = None,
    ) -> CustomerInfo:
        customer_id = f"mock_cust_{str(uuid.uuid4())[:8]}"
        logger.info("mock_create_customer", email=email, customer_id=customer_id)
        return CustomerInfo(
            provider_customer_id=customer_id,
            email=email,
            name=name,
            provider="mock",
        )

    async def create_subscription(
        self,
        customer_id: str,
        plan: str,
        interval: BillingInterval = BillingInterval.MONTHLY,
        trial_days: int = 14,
    ) -> SubscriptionInfo:
        sub_id = f"mock_sub_{str(uuid.uuid4())[:8]}"
        now = datetime.now(timezone.utc)
        plan_info = MOCK_PLANS.get(plan, MOCK_PLANS["starter"])

        amount = plan_info["amount"]
        if interval == BillingInterval.ANNUAL:
            amount = amount * 10  # 2 months free

        trial_end = now + timedelta(days=trial_days) if trial_days else None
        period_end = now + timedelta(days=30 if interval == BillingInterval.MONTHLY else 365)

        logger.info("mock_create_subscription", plan=plan, sub_id=sub_id)

        return SubscriptionInfo(
            provider_subscription_id=sub_id,
            provider_customer_id=customer_id,
            plan=plan,
            status=SubscriptionStatus.TRIALING if trial_days else SubscriptionStatus.ACTIVE,
            interval=interval,
            amount=amount,
            currency=plan_info["currency"],
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=False,
            trial_end=trial_end,
        )

    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_immediately: bool = False,
    ) -> SubscriptionInfo:
        now = datetime.now(timezone.utc)
        logger.info("mock_cancel_subscription", sub_id=subscription_id)
        return SubscriptionInfo(
            provider_subscription_id=subscription_id,
            provider_customer_id="mock_cust",
            plan="free",
            status=SubscriptionStatus.CANCELLED,
            interval=BillingInterval.MONTHLY,
            amount=0,
            currency="INR",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=not cancel_immediately,
        )

    async def get_subscription(
        self,
        subscription_id: str,
    ) -> SubscriptionInfo | None:
        now = datetime.now(timezone.utc)
        return SubscriptionInfo(
            provider_subscription_id=subscription_id,
            provider_customer_id="mock_cust",
            plan="professional",
            status=SubscriptionStatus.ACTIVE,
            interval=BillingInterval.MONTHLY,
            amount=16499,
            currency="INR",
            current_period_start=now - timedelta(days=15),
            current_period_end=now + timedelta(days=15),
        )

    async def get_invoices(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> list[InvoiceInfo]:
        now = datetime.now(timezone.utc)
        invoices = []
        for i in range(min(3, limit)):
            month_start = now - timedelta(days=30 * (i + 1))
            invoices.append(InvoiceInfo(
                provider_invoice_id=f"mock_inv_{str(uuid.uuid4())[:8]}",
                amount=16499 * 1.18,  # with GST
                currency="INR",
                status="paid",
                period_start=month_start,
                period_end=month_start + timedelta(days=30),
                invoice_url=None,
                invoice_pdf=None,
            ))
        return invoices

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        return f"{return_url}?mock_billing=true"
