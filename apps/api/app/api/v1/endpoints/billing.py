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
    plan:   str
    addon:  bool = False
    period: str  = "monthly"  # monthly | 6months | 12months


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


    PERIOD_MONTHS = {"monthly": 1, "6months": 5, "12months": 10}
    period_months = PERIOD_MONTHS.get(req.period, 1)
    GST_RATE = 0.18

    base_amount  = PLAN_AMOUNTS[req.plan] * period_months
    addon_amount = ADDON_AMOUNTS.get(req.plan, 0) * period_months if req.addon else 0
    subtotal     = base_amount + addon_amount
    gst_amount   = int(subtotal * GST_RATE)
    amount       = subtotal + gst_amount
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

    # Activate plan
    update_vals: dict = {"plan": req.plan}
    if req.addon:
        update_vals["addon_enabled"] = True

    await db.execute(
        update(Organisation)
        .where(Organisation.id == user.org_id)
        .values(**update_vals)
    )
    await db.commit()

    logger.info("razorpay_payment_verified",
        org_id=str(user.org_id), plan=req.plan,
        payment_id=req.razorpay_payment_id)

    return {
        "success": True,
        "plan":    req.plan,
        "message": f"Payment verified. Successfully upgraded to {req.plan} plan.",
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
            "id":           d.get("payment_id",""),
            "order_id":     d.get("order_id",""),
            "plan":         d.get("plan",""),
            "addon":        d.get("addon", False),
            "period":       d.get("period","monthly"),
            "base_amount":  d.get("base_amount", 0),
            "addon_amount": d.get("addon_amount", 0),
            "gst_amount":   d.get("gst_amount", 0),
            "total_amount": d.get("total_amount", 0),
            "provider":     "razorpay",
            "created_at":   row[1].isoformat() if row[1] else "",
            "status":       "paid",
        })
    return {"payments": payments, "total": len(payments)}
