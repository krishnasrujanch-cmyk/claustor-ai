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


async def _fetch_billing_extra(session, organisation_id) -> dict:
    """Get fresh billing expiry fields via raw SQL — avoids ORM cache."""
    from sqlalchemy import text
    r = await session.execute(text("""
        SELECT payment_status, next_billing_date, grace_period_end,
               billing_period, addon_enabled
        FROM organisations WHERE id = :id
    """), {"id": str(organisation_id)})
    row = r.fetchone()
    if not row:
        return {}
    return {
        "payment_status":    row[0] or "active",
        "next_billing_date": row[1].isoformat() if row[1] else None,
        "grace_period_end":  row[2].isoformat() if row[2] else None,
        "billing_period":    row[3] or "monthly",
        "addon_enabled":     row[4] or False,
    }


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
        **(await _fetch_billing_extra(db, user.org_id)),
    }


@router.post("/upgrade")
async def upgrade_plan(
    req: UpgradeRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upgrade or downgrade plan. Works for any plan change."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can change plan")

    if req.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {req.plan}")

    if req.plan == "enterprise":
        raise HTTPException(status_code=400,
            detail="Enterprise requires custom setup. Contact hello@claustor.ai")

    # Direct plan update in DB (no payment processor in dev)
    from sqlalchemy import update
    from app.domain.models import Organisation
    await db.execute(
        update(Organisation)
        .where(Organisation.id == user.org_id)
        .values(plan=req.plan)
    )
    await db.commit()

    action = "upgraded" if req.plan != "free" else "downgraded"
    return {
        "success": True,
        "plan": req.plan,
        "message": f"Successfully {action} to {req.plan} plan.",
    }


@router.get("/invoice/{invoice_index}/pdf")
async def download_invoice_pdf(
    invoice_index: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and download invoice PDF."""
    import io
    from fastapi.responses import StreamingResponse
    from datetime import datetime

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.units import cm

        # Get org info
        from app.domain.models import Organisation
        from sqlalchemy import select
        org_result = await db.execute(
            select(Organisation).where(Organisation.id == user.org_id)
        )
        org = org_result.scalar_one_or_none()
        plan = org.plan if org else "professional"
        plan_prices = {"free":0,"starter":3999,"professional":16499,"enterprise":0}
        base = plan_prices.get(plan, 0)
        gst = round(base * 0.18)
        total = base + gst
        now = datetime.now()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2*cm, rightMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("<b>CLAUSTOR AI</b>", styles["Heading1"]))
        story.append(Paragraph("DKU Technologies Pvt. Ltd.", styles["Normal"]))
        story.append(Paragraph("Hyderabad, India | hello@claustor.ai", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"<b>TAX INVOICE</b>", styles["Heading2"]))
        story.append(Paragraph(f"Invoice #{invoice_index+1:04d} | {now.strftime('%d %b %Y')}", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        data = [
            ["Description", "Amount (INR)"],
            [f"{plan.title()} Plan - {now.strftime('%B %Y')}", f"₹{base:,}"],
            ["GST @ 18%", f"₹{gst:,}"],
            ["Total", f"₹{total:,}"],
        ]
        t = Table(data, colWidths=[12*cm, 5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), rl_colors.HexColor("#0066FF")),
            ("TEXTCOLOR",  (0,0), (-1,0), rl_colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN",      (1,0), (1,-1), "RIGHT"),
            ("GRID",       (0,0), (-1,-1), 0.5, rl_colors.HexColor("#E5E7EB")),
            ("FONTNAME",   (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), rl_colors.HexColor("#F0F7FF")),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Thank you for using Claustor AI.", styles["Normal"]))
        doc.build(story)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=claustor-invoice-{invoice_index+1:04d}.pdf"})

    except ImportError:
        # Fallback text invoice
        import io as _io
        text = f"""CLAUSTOR AI - TAX INVOICE
DKU Technologies Pvt. Ltd.
Invoice #{invoice_index+1:04d} | {datetime.now().strftime('%d %b %Y')}

Plan: {plan.title()}
Amount: INR {base:,}
GST (18%): INR {gst:,}
Total: INR {total:,}

Thank you for using Claustor AI.
"""
        return StreamingResponse(_io.BytesIO(text.encode()),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=claustor-invoice-{invoice_index+1:04d}.txt"})

# ── Razorpay Standard Checkout ────────────────────────────────────

class RazorpayOrderRequest(BaseModel):
    plan:         str
    addon:        bool = False
    period:       str  = "monthly"
    apply_credit: bool = True   # apply pro-rata credit if available


@router.post("/razorpay/create-order")
async def razorpay_create_order(
    req: RazorpayOrderRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Razorpay order for plan upgrade."""
    from app.core.config import settings
    import razorpay
    import uuid as _uuid

    PLAN_AMOUNTS = {
        "starter":      399900,   # ₹3,999 in paise
        "professional": 1649900,  # ₹16,499 in paise
    }
    ADDON_AMOUNTS = {
        "starter":      100000,   # ₹1,000
        "professional": 250000,   # ₹2,500
    }

    if req.plan not in PLAN_AMOUNTS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {req.plan}")

    amount = PLAN_AMOUNTS[req.plan]
    if req.addon:
        amount += ADDON_AMOUNTS.get(req.plan, 0)

    if amount < 100:
        raise HTTPException(status_code=400, detail="Amount must be at least ₹1")

    if not settings.RAZORPAY_KEY_ID:
        raise HTTPException(status_code=503, detail="Razorpay not configured")

    try:
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order = client.order.create({
            "amount":   amount,
            "currency": "INR",
            "receipt":  f"claustor_{str(user.org_id)[:8]}_{_uuid.uuid4().hex[:8]}",
            "notes": {
                "org_id": str(user.org_id),
                "plan":   req.plan,
                "addon":  str(req.addon),
            },
        })
        return {
            "order_id": order["id"],
            "amount":   order["amount"],
            "currency": order["currency"],
            "key_id":   settings.RAZORPAY_KEY_ID,
        }
    except Exception as e:
        logger.error("razorpay_create_order_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create payment order")


class RazorpayVerifyRequest(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str
    plan:                str
    addon:               bool = False
    period:              str  = "monthly"
    total_amount:        int  = 0


@router.post("/razorpay/verify-payment")
async def razorpay_verify_payment(
    req: RazorpayVerifyRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay payment signature and activate plan."""
    import hmac
    import hashlib
    from app.core.config import settings
    from sqlalchemy import update
    from app.domain.models import Organisation

    if not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay not configured")

    # Verify HMAC-SHA256 signature
    payload   = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    expected  = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, req.razorpay_signature):
        logger.warning("razorpay_signature_mismatch",
            org_id=str(user.org_id), order_id=req.razorpay_order_id)
        raise HTTPException(status_code=400, detail="Payment verification failed")

    # Calculate next billing date based on period
    from datetime import datetime, timezone, timedelta
    from app.core.pricing import BILLING_PERIODS
    period_info  = BILLING_PERIODS.get(req.period, BILLING_PERIODS["monthly"])
    total_months = period_info["charge_months"] + period_info["free_months"]
    now          = datetime.now(timezone.utc)
    # Approximate months as 30 days each
    next_billing = now + timedelta(days=total_months * 30)

    # Activate plan with expiry tracking (raw SQL to avoid ORM column cache)
    from sqlalchemy import text as _txt
    await db.execute(_txt("""
        UPDATE organisations SET
            plan                = :plan,
            addon_enabled       = :addon,
            payment_status      = 'active',
            next_billing_date   = :next_billing,
            last_payment_date   = :now,
            last_payment_amount = :amount,
            billing_period      = :period,
            grace_period_end    = NULL,
            reminder_sent_days  = ARRAY[]::integer[]
        WHERE id = :org_id
    """), {
        "plan":         req.plan,
        "addon":        req.addon,
        "next_billing": next_billing,
        "now":          now,
        "amount":       int(req.total_amount) if hasattr(req,"total_amount") else 0,
        "period":       req.period,
        "org_id":       str(user.org_id),
    })
    await db.commit()

    logger.info("razorpay_payment_verified",
        org_id=str(user.org_id), plan=req.plan,
        payment_id=req.razorpay_payment_id)

    return {
        "success": True,
        "plan":    req.plan,
        "message": f"Payment verified. Successfully upgraded to {req.plan} plan.",
    }

# ── Pro-rata Credit Calculation ───────────────────────────────────

@router.get("/razorpay/prorate")
async def get_prorate_credit(
    target_plan: str,
    period:      str = "monthly",
    addon:       bool = False,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate pro-rata credit for starter → professional upgrade.
    Returns full breakdown: new price, credit, amount to pay.
    """
    from sqlalchemy import text
    from app.core.pricing import calculate_amount, calculate_prorate_credit
    from datetime import datetime, timezone

    # Block invalid upgrades
    UPGRADE_RULES = {
        ("free",         "starter"):      True,
        ("free",         "professional"): True,
        ("starter",      "professional"): True,
        ("professional", "starter"):      False,  # blocked
        ("professional", "free"):         False,  # blocked
    }

    r = await db.execute(text("""
        SELECT plan, next_billing_date, last_payment_amount,
               billing_period, payment_status
        FROM organisations WHERE id = :id
    """), {"id": str(user.org_id)})
    org = r.fetchone()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    current_plan, next_billing, last_amount, billing_period, payment_status = org

    # Check upgrade rules
    allowed = UPGRADE_RULES.get((current_plan, target_plan), True)
    if not allowed:
        raise HTTPException(status_code=400,
            detail=f"Downgrade from {current_plan} to {target_plan} is not allowed")

    # Calculate new plan price
    pricing = calculate_amount(target_plan, addon, period)

    # Calculate credit (only for starter → professional)
    credit_info = {"credit": 0, "daily_rate": 0, "remaining_days": 0}
    if current_plan == "starter" and target_plan == "professional":
        credit_info = calculate_prorate_credit(
            current_plan   = current_plan,
            last_payment_amount = last_amount or 0,
            billing_period = billing_period or "monthly",
            next_billing_date   = next_billing,
        )

    # Apply credit
    credit        = credit_info["credit"]
    subtotal      = pricing["base_amount"] + pricing["addon_amount"]
    credit_applied = min(credit, subtotal)  # can't credit more than new price
    discounted     = max(0, subtotal - credit_applied)
    gst            = round(discounted * 0.18)
    total_to_pay   = discounted + gst
    total_paise    = total_to_pay * 100

    return {
        "current_plan":    current_plan,
        "target_plan":     target_plan,
        "period":          period,
        "addon":           addon,
        "new_plan_price":  subtotal,
        "credit_applied":  credit_applied,
        "remaining_days":  credit_info["remaining_days"],
        "daily_rate":      credit_info["daily_rate"],
        "discounted_base": discounted,
        "gst":             gst,
        "total_to_pay":    total_to_pay,
        "total_paise":     total_paise,
        "is_upgrade":      allowed,
        "has_credit":      credit_applied > 0,
    }


@router.get("/razorpay/payments")
async def get_razorpay_payments(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get Razorpay payment history from audit log."""
    from sqlalchemy import text
    r = await db.execute(text("""
        SELECT extra_data, created_at
        FROM audit_log
        WHERE org_id = :org_id
          AND action = 'payment_completed'
        ORDER BY created_at DESC
        LIMIT 20
    """), {"org_id": str(user.org_id)})
    rows = r.fetchall()
    payments = []
    for row in rows:
        d = row[0] or {}
        payments.append({
            "id":           d.get("payment_id", ""),
            "order_id":     d.get("order_id", ""),
            "plan":         d.get("plan", ""),
            "addon":        d.get("addon", False),
            "period":       d.get("period", "monthly"),
            "base_amount":  d.get("base_amount", 0),
            "addon_amount": d.get("addon_amount", 0),
            "gst_amount":   d.get("gst_amount", 0),
            "total_amount": d.get("total_amount", 0),
            "provider":     "razorpay",
            "created_at":   row[1].isoformat() if row[1] else "",
            "status":       "paid",
        })
    return {"payments": payments, "total": len(payments)}
