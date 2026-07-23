"""
Claustor AI — Billing Endpoints
Subscription management, usage, invoices, plan upgrade.
Works with Mock (dev) → Stripe (intl) → Razorpay (India).
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import get_db
from app.services.billing.billing_service import BillingService, PLANS
from app.services.billing.base import BillingInterval

logger = structlog.get_logger(__name__)
router = APIRouter()


class UpgradeRequest(BaseModel):
    plan: str
    interval: str = "monthly"


class CancelRequest(BaseModel):
    cancel_immediately: bool = False


@router.get("/usage")
async def get_usage(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage stats for the organisation."""
    service = BillingService(db)
    usage = await service.get_usage(user.org_id)
    return usage


@router.get("/plans")
async def list_plans():
    """List all available plans with features and pricing."""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_inr": 0,
                "price_usd": 0,
                "interval": "forever",
                "users": 1,
                "contracts": 5,
                "queries": 100,
                "storage_gb": 0.1,
                "features": PLANS["free"]["features"],
                "cta": "Get started",
            },
            {
                "id": "starter",
                "name": "Starter",
                "price_inr": 3999,
                "price_usd": 49,
                "price_inr_annual": 39990,
                "interval": "monthly",
                "users": 10,
                "extra_user_price_inr": 299,
                "contracts": 100,
                "queries": 5000,
                "storage_gb": 10,
                "features": PLANS["starter"]["features"],
                "cta": "Start trial",
                "trial_days": 14,
            },
            {
                "id": "professional",
                "name": "Professional",
                "price_inr": 16499,
                "price_usd": 199,
                "price_inr_annual": 164990,
                "interval": "monthly",
                "users": 50,
                "extra_user_price_inr": 399,
                "contracts": 1000,
                "queries": 50000,
                "storage_gb": 100,
                "features": PLANS["professional"]["features"],
                "cta": "Start trial",
                "trial_days": 14,
                "popular": True,
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price_inr": None,
                "price_usd": None,
                "interval": "custom",
                "users": -1,
                "contracts": -1,
                "queries": -1,
                "storage_gb": -1,
                "features": ["all"],
                "cta": "Talk to sales",
                "contact": "hello@claustor.com",
            },
        ]
    }


@router.post("/subscribe")
async def subscribe(
    req: UpgradeRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Subscribe to a plan.
    Creates customer + subscription in billing provider.
    14-day free trial on first subscription.
    """
    if req.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {req.plan}")

    if req.plan == "free":
        raise HTTPException(status_code=400, detail="Cannot subscribe to free plan")

    if req.plan == "enterprise":
        raise HTTPException(
            status_code=400,
            detail="Enterprise requires custom setup. Contact hello@claustor.com"
        )

    interval = BillingInterval.ANNUAL if req.interval == "annual" else BillingInterval.MONTHLY

    service = BillingService(db)
    result = await service.create_subscription(
        org_id=user.org_id,
        plan=req.plan,
        email=user.email,
        org_name=f"Org {user.org_id}",
        interval=interval,
    )

    return {
        **result,
        "message": f"Successfully subscribed to {req.plan} plan. 14-day free trial started.",
    }


@router.post("/cancel")
async def cancel_subscription(
    req: CancelRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel subscription. Downgrades to free at period end."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can cancel subscription")

    service = BillingService(db)
    result = await service.cancel_subscription(
        org_id=user.org_id,
        cancel_immediately=req.cancel_immediately,
    )
    return {
        **result,
        "message": "Subscription cancelled. " + (
            "Access ends immediately." if req.cancel_immediately
            else "Access continues until end of billing period."
        ),
    }


@router.get("/invoices")
async def get_invoices(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get invoice history for the organisation."""
    service = BillingService(db)
    invoices = await service.get_invoices(user.org_id)
    return {"invoices": invoices, "total": len(invoices)}


@router.get("/portal")
async def billing_portal(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get billing portal URL.
    Stripe: full portal (payment methods, invoices, plan changes)
    Razorpay: redirect to billing page
    Mock: returns mock URL
    """
    from app.core.config import settings
    service = BillingService(db)
    from sqlalchemy import select
    from app.domain.models import Organisation

    result = await db.execute(
        select(Organisation.stripe_customer_id)
        .where(Organisation.id == user.org_id)
    )
    row = result.first()

    if not row or not row.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No billing account found. Please subscribe to a plan first."
        )

    portal_url = await service.provider.create_portal_session(
        customer_id=row.stripe_customer_id,
        return_url=f"{settings.APP_URL}/dashboard/billing",
    )
    return {"portal_url": portal_url}


@router.get("/summary")
async def billing_summary(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full billing summary — plan + usage + next invoice."""
    from sqlalchemy import select
    from app.domain.models import Organisation

    result = await db.execute(
        select(
            Organisation.plan,
            Organisation.plan_started_at,
            Organisation.plan_expires_at,
            Organisation.stripe_customer_id,
            Organisation.stripe_subscription_id,
            Organisation.contracts_used,
            Organisation.queries_used,
            Organisation.max_contracts,
            Organisation.max_queries_mo,
            Organisation.max_users,
            Organisation.extra_users_purchased,
        ).where(Organisation.id == user.org_id)
    )
    org = result.first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    service = BillingService(db)
    usage = await service.get_usage(user.org_id)

    plan_info = PLANS.get(org.plan, PLANS["free"])

    return {
        "plan": org.plan,
        "plan_started_at": org.plan_started_at.isoformat() if org.plan_started_at else None,
        "plan_expires_at": org.plan_expires_at.isoformat() if org.plan_expires_at else None,
        "billing_provider": service.provider.get_provider_name(),
        "has_subscription": bool(org.stripe_subscription_id),
        "usage": usage.get("usage", {}),
        "features": plan_info.get("features", []),
        "extra_users_purchased": org.extra_users_purchased or 0,
        "upgrade_available": org.plan != "enterprise",
    }
