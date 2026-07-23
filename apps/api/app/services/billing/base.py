"""
Claustor AI — Billing Provider Base
Abstract interface for billing providers.
Swap Stripe ↔ Razorpay ↔ Mock via config.
Same pattern as LLMRouter.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    ANNUAL  = "annual"


class SubscriptionStatus(str, Enum):
    ACTIVE    = "active"
    CANCELLED = "cancelled"
    PAST_DUE  = "past_due"
    TRIALING  = "trialing"
    PAUSED    = "paused"


@dataclass
class CustomerInfo:
    provider_customer_id: str
    email: str
    name: str
    provider: str


@dataclass
class SubscriptionInfo:
    provider_subscription_id: str
    provider_customer_id: str
    plan: str
    status: SubscriptionStatus
    interval: BillingInterval
    amount: float
    currency: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    trial_end: datetime | None = None


@dataclass
class InvoiceInfo:
    provider_invoice_id: str
    amount: float
    currency: str
    status: str
    period_start: datetime
    period_end: datetime
    invoice_url: str | None = None
    invoice_pdf: str | None = None


class BaseBillingProvider(ABC):
    """
    Abstract billing provider interface.
    All providers implement this — business logic never
    imports Stripe/Razorpay directly.
    """

    @abstractmethod
    async def create_customer(
        self,
        email: str,
        name: str,
        org_id: str,
        metadata: dict | None = None,
    ) -> CustomerInfo:
        ...

    @abstractmethod
    async def create_subscription(
        self,
        customer_id: str,
        plan: str,
        interval: BillingInterval = BillingInterval.MONTHLY,
        trial_days: int = 0,
    ) -> SubscriptionInfo:
        ...

    @abstractmethod
    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_immediately: bool = False,
    ) -> SubscriptionInfo:
        ...

    @abstractmethod
    async def get_subscription(
        self,
        subscription_id: str,
    ) -> SubscriptionInfo | None:
        ...

    @abstractmethod
    async def get_invoices(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> list[InvoiceInfo]:
        ...

    @abstractmethod
    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """Returns URL to billing portal."""
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        ...
