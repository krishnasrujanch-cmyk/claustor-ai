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
                "price_inr": 7999,
                "price_usd": 96,
                "price_inr_annual": 81590,
                "interval": "monthly",
                "users": 5,
                "extra_user_price_inr": 800,
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
                "price_inr": 29999,
                "price_usd": 357,
                "price_inr_annual": 287990,
                "interval": "monthly",
                "users": 25,
                "extra_user_price_inr": 1500,
                "contracts": 500,
                "queries": 25000,
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
                "contact": "support@claustor.com",
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
            detail="Enterprise requires custom setup. Contact support@claustor.com"
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
        select(Organisation).where(Organisation.id == user.org_id)
    )
    org = result.scalar_one_or_none()
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
        "org_name": org.name if hasattr(org, "name") else "",
        "org_gstin": getattr(org, "gstin", "") or "",
        "org_address": getattr(org, "address", "") or "",
        "org_phone": getattr(org, "phone", "") or "",
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
            detail="Enterprise requires custom setup. Contact support@claustor.com")

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
        if org: await db.refresh(org)
        # Fetch actual payment amount for this specific invoice
        _actual_payment = 0
        _actual_billing_pd = org.billing_period if org else "monthly"
        try:
            _svc = BillingService(db)
            _invs = await _svc.get_invoices(user.org_id)
            if invoice_index < len(_invs):
                _actual_payment = _invs[invoice_index]["amount"]
        except Exception:
            pass
        plan = org.plan if org else "professional"
        plan_prices = {"free":0,"starter":7999,"professional":29999,"enterprise":99999}
        # Use actual last_payment_amount from org if available
        last_paid = _actual_payment if _actual_payment > 0 else (org.last_payment_amount if org and org.last_payment_amount else 0)
        billing_pd = _actual_billing_pd if _actual_billing_pd else (org.billing_period if org and org.billing_period else "monthly")
        period_months = {"monthly":1,"6months":5,"12months":10}.get(billing_pd, 1)
        plan_monthly = plan_prices.get(plan, 0)
        base = plan_monthly * period_months
        # Use actual paid amount for total
        total = last_paid if last_paid > 0 else round(base * 1.18)
        subtotal_raw = round(total / 1.18)
        gst = total - subtotal_raw
        now = datetime.now()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2*cm, rightMargin=2*cm)
        styles = getSampleStyleSheet()
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
        from reportlab.platypus import HRFlowable
        BLUE = rl_colors.HexColor("#0066FF")
        story = []

        # Header: Claustor + Invoice details
        hdr = [[
            Paragraph(
                "<b><font size=18 color='#0066FF'>Claustor AI</font></b><br/>"
                "<font size=8 color='#6B7280'>DKU Technologies Pvt. Ltd.<br/>"
                "Hyderabad, Telangana - 500032<br/>"
                "GSTIN: 36AATFD9569L1ZC<br/>"
                "billing@claustor.ai</font>",
                styles["Normal"]),
            Paragraph(
                f"<b><font size=14>TAX INVOICE</font></b><br/>"
                f"<font size=8 color='#6B7280'>"
                f"Invoice: INV-{now.strftime('%Y%m')}-{invoice_index+1:04d}<br/>"
                f"Date: {now.strftime('%d %b %Y')}<br/>"
                f"<font color='#22C55E'><b>PAID</b></font></font>",
                ParagraphStyle('r', alignment=TA_RIGHT, fontSize=9)),
        ]]
        ht = Table(hdr, colWidths=[9*cm, 8*cm])
        ht.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),0)]))
        story.append(ht)
        story.append(Spacer(1, 0.2*cm))
        story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=6))

        # Bill To with org GSTIN
        bill_lines = ["<b>Bill To:</b>"]
        bill_lines.append(f"<b>{org.name}</b>" if org and org.name else "<b>Organisation</b>")
        if org and getattr(org, "address", None):
            bill_lines.append(org.address)
        if org and getattr(org, "phone", None):
            bill_lines.append(f"Phone: {org.phone}")
        if org and getattr(org, "gstin", None):
            bill_lines.append(f"<b>GSTIN: {org.gstin}</b>")
        story.append(Paragraph("<br/>".join(bill_lines),
            ParagraphStyle("bt", fontSize=9, leading=14,
                backColor=rl_colors.HexColor("#F8FAFC"), borderPadding=8)))
        story.append(Spacer(1, 0.3*cm))

        # Invoice table
        period_labels = {"monthly":"Monthly","6months":"6 Months","12months":"12 Months"}
        period_label = period_labels.get(billing_pd, "Monthly")
        period_months = {"monthly":1,"6months":5,"12months":10}.get(billing_pd, 1)
        idata = [["#","Description","Period","Amount (INR)"]]
        idata.append(["1", f"{plan.title()} Plan × {period_months} months", period_label, f"\u20b9{base:,}"])
        if total < base and (base - subtotal_raw) > 0:
            credit = base - subtotal_raw
            idata.append(["","Pro-rata Credit (Starter balance)","",f"-\u20b9{credit:,}"])
            idata.append(["","Net Payable","",f"\u20b9{subtotal_raw:,}"])
        idata.append(["","GST @ 18% (IGST)","",f"\u20b9{gst:,}"])
        idata.append(["","Total Charged","",f"\u20b9{total:,}"])
        t = Table(idata, colWidths=[1*cm, 9*cm, 3.5*cm, 3.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), BLUE),
            ("TEXTCOLOR",(0,0),(-1,0), rl_colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1), 9),
            ("ALIGN",(3,0),(3,-1),"RIGHT"),
            ("GRID",(0,0),(-1,-1), 0.4, rl_colors.HexColor("#E5E7EB")),
            ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
            ("BACKGROUND",(0,-1),(-1,-1), rl_colors.HexColor("#EFF6FF")),
            ("ROWBACKGROUNDS",(0,1),(-1,-2),[rl_colors.white, rl_colors.HexColor("#F8FAFC")]),
            ("PADDING",(0,0),(-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            f"<font size=8 color='#6B7280'>Amount in words: <b>Rupees {total:,} only</b></font>",
            styles["Normal"]))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=0.5,
            color=rl_colors.HexColor("#E5E7EB"), spaceAfter=4))
        story.append(Paragraph(
            "<font size=7 color='#6B7280'>"
            "Computer-generated invoice. Queries: billing@claustor.ai | "
            "DKU Technologies Pvt. Ltd., Hyderabad.</font>", styles["Normal"]))
        story.append(Paragraph(
            "<font size=9 color='#0066FF'><b>Thank you for using Claustor AI!</b></font>",
            ParagraphStyle("ty", alignment=TA_CENTER)))
        doc.build(story)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=claustor-invoice-{invoice_index+1:04d}.pdf"})

    except Exception as _inv_err:
        print(f"INVOICE ERROR: {_inv_err}", flush=True)
        import traceback; traceback.print_exc()
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

    from app.core.pricing import calculate_amount, calculate_prorate_credit, PLAN_PRICING
    from sqlalchemy import text as _txt_co
    if req.plan not in PLAN_PRICING:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {req.plan}")

    pricing      = calculate_amount(req.plan, req.addon, req.period)
    base_amount  = pricing["base_amount"]
    addon_amount = pricing["addon_amount"]
    period_months = pricing["period_months"]

    # Apply pro-rata credit for starter → professional upgrade
    credit_applied = 0
    if req.apply_credit and req.plan == "professional":
        r_org = await db.execute(_txt_co("""
            SELECT plan, next_billing_date, last_payment_amount, billing_period
            FROM organisations WHERE id = :id
        """), {"id": str(user.org_id)})
        org_row = r_org.fetchone()
        if org_row and org_row[0] == "starter":
            credit_info = calculate_prorate_credit(
                current_plan        = org_row[0],
                last_payment_amount = org_row[2] or 0,
                billing_period      = org_row[3] or "monthly",
                next_billing_date   = org_row[1],
            )
            credit_applied = min(credit_info["credit"], base_amount + addon_amount)

    subtotal   = max(0, base_amount + addon_amount - credit_applied)
    gst_amount = round(subtotal * 0.18)
    total_inr  = subtotal + gst_amount
    amount     = total_inr * 100  # paise

    if amount < 100:
        amount = 100
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
                "org_id":        str(user.org_id),
                "plan":          req.plan,
                "addon":         str(req.addon),
                "period":        req.period,
                "credit_applied":str(credit_applied),
            },
        })
        return {
            "order_id":  order["id"],
            "amount":    order["amount"],
            "currency":  order["currency"],
            "key_id":    settings.RAZORPAY_KEY_ID,
            "breakdown": {
                "base":           base_amount,
                "addon":          addon_amount,
                "credit_applied": credit_applied,
                "gst":            gst_amount,
                "total":          total_inr,
            },
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
    free_upgrade:        bool = False
    extended_days:       int  = 0


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

    # Skip signature check for free upgrades (credit covers full amount)
    if not req.free_upgrade:
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
    if req.free_upgrade and req.extended_days > 0:
        next_billing = now + timedelta(days=req.extended_days)
    else:
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
            grace_period_end    = NULL
        WHERE id = :org_id
    """), {
        "plan":         req.plan,
        "addon":        req.addon,
        "next_billing": next_billing,
        "now":          now,
        "amount":       int(req.total_amount) if hasattr(req,"total_amount") and req.total_amount else 0,
        "period":       req.period,
        "org_id":       str(user.org_id),
    })
    await db.commit()

    # Save payment to audit log
    try:
        import uuid as _uuid3, json as _json3
        from app.domain.models.models import AuditLog
        from app.core.pricing import calculate_amount
        pricing = calculate_amount(req.plan, req.addon, req.period)
        db.add(AuditLog(
            id=_uuid3.uuid4(),
            org_id=user.org_id,
            user_id=user.id,
            user_role=user.role,
            action="payment_completed",
            resource_type="billing",
            resource_id=_uuid3.uuid4(),
            status="success",
            extra_data={
                "payment_id":    req.razorpay_payment_id,
                "order_id":      req.razorpay_order_id,
                "plan":          req.plan,
                "addon":         req.addon,
                "period":        req.period,
                "base_amount":   pricing["base_amount"],
                "addon_amount":  pricing["addon_amount"],
                "gst_amount":    pricing["gst_amount"],
                "total_amount":  int(req.total_amount) if hasattr(req,"total_amount") else pricing["total"],
                "provider":      "razorpay",
                "timestamp":     now.isoformat(),
            },
        ))
        await db.commit()
    except Exception as _ae:
        logger.warning("audit_log_failed", error=str(_ae))

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
    from app.core.pricing import BILLING_PERIODS, calculate_amount
    credit        = credit_info["credit"]
    subtotal      = pricing["base_amount"] + pricing["addon_amount"]
    period_info   = BILLING_PERIODS.get(period, BILLING_PERIODS["monthly"])
    new_days      = (period_info["charge_months"] + period_info["free_months"]) * 30

    if credit >= subtotal:
        # Credit covers full plan — free upgrade + extend expiry by remaining credit days
        credit_applied   = subtotal
        discounted       = 0
        gst              = 0
        total_to_pay     = 0
        total_paise      = 0
        # Extra credit days — use Professional daily rate
        extra_credit_inr  = credit - subtotal
        pro_daily_rate    = subtotal / 30  # professional monthly / 30 days
        extra_days        = round(extra_credit_inr / pro_daily_rate) if pro_daily_rate > 0 else 0
        extended_days     = new_days + extra_days
    else:
        credit_applied   = credit
        discounted       = max(0, subtotal - credit_applied)
        gst              = round(discounted * 0.18)
        total_to_pay     = discounted + gst
        total_paise      = total_to_pay * 100
        extra_days       = 0
        extended_days    = new_days

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
        "free_upgrade":    credit >= subtotal,
        "extended_days":   extended_days,
        "extra_days":      extra_days,
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


# Plan limits — update here when changing plan tiers
PLAN_LIMITS = {
    "free":         {"max_contracts": 5,       "max_queries_mo": 100,    "max_storage_mb": 100},
    "starter":      {"max_contracts": 100,     "max_queries_mo": 5000,   "max_storage_mb": 1000},
    "professional": {"max_contracts": 1000,    "max_queries_mo": 50000,  "max_storage_mb": 10000},
    "enterprise":   {"max_contracts": -1,      "max_queries_mo": -1,     "max_storage_mb": -1},
}


# ── Enterprise Lead Form ──────────────────────────────────────────

class EnterpriseLeadRequest(BaseModel):
    business_name:        str
    industry:             str
    company_size:         str
    contact_name:         str
    business_email:       str
    mobile:               str = ""
    contracts_per_month:  str = ""
    message:              str = ""


@router.post("/enterprise/contact")
async def enterprise_contact(
    req: EnterpriseLeadRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit enterprise contact — emails sales team + auto-reply."""
    import httpx
    from app.core.config import settings

    if "@" not in req.business_email or "." not in req.business_email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    sales_html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;padding:32px;color:#111827">
  <div style="font-size:20px;font-weight:900;color:#0066FF;margin-bottom:24px">⚡ New Enterprise Lead — Claustor AI</div>
  <table style="width:100%;border-collapse:collapse">
    <tr><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;width:40%">Business</td><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:600">{req.business_name}</td></tr>
    <tr><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280">Industry</td><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:600">{req.industry}</td></tr>
    <tr><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280">Size</td><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:600">{req.company_size}</td></tr>
    <tr><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280">Contact</td><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:600">{req.contact_name}</td></tr>
    <tr><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280">Email</td><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:600">{req.business_email}</td></tr>
    <tr><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280">Mobile</td><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:600">{req.mobile or "—"}</td></tr>
    <tr><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;color:#6B7280">Contracts/mo</td><td style="padding:8px 0;border-bottom:1px solid #E5E7EB;font-weight:600">{req.contracts_per_month or "—"}</td></tr>
    <tr><td style="padding:8px 0;color:#6B7280;vertical-align:top">Message</td><td style="padding:8px 0">{req.message or "—"}</td></tr>
  </table>
  <div style="margin-top:20px;padding:12px;background:#EFF6FF;border-radius:8px;font-size:13px;color:#1D4ED8">Submitted by: {user.email}</div>
</div>"""

    customer_html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;padding:32px;color:#111827">
  <div style="font-size:20px;font-weight:900;color:#0066FF;margin-bottom:16px">Claustor AI</div>
  <p>Hi {req.contact_name},</p>
  <p style="margin:12px 0">Thank you for your interest in Claustor AI Enterprise. Our sales team will reach out within <strong>1 business day</strong>.</p>
  <div style="background:#F8FAFC;border:1px solid #E5E7EB;border-radius:8px;padding:16px;margin:16px 0;font-size:13px;line-height:1.8">
    <strong>{req.business_name}</strong> · {req.industry} · {req.company_size}
  </div>
  <p style="font-size:13px;color:#6B7280">Direct contact: <a href="mailto:support@claustor.com" style="color:#0066FF">support@claustor.com</a></p>
  <p style="margin-top:24px;font-size:11px;color:#9CA3AF">Claustor AI · DKU Technologies Pvt. Ltd.</p>
</div>"""

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post("https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": f"Claustor AI <{settings.RESEND_FROM}>", "to": ["support@claustor.com"],
                      "subject": f"Enterprise Lead: {req.business_name} ({req.industry})", "html": sales_html})
            await client.post("https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": f"Claustor AI <{settings.RESEND_FROM}>", "to": [req.business_email],
                      "subject": "We received your Enterprise inquiry — Claustor AI", "html": customer_html})
    except Exception as e:
        logger.warning("enterprise_lead_email_failed", error=str(e))

    logger.info("enterprise_lead_received", business=req.business_name, email=req.business_email)
    return {"success": True, "message": "Request received! We'll contact you within 1 business day."}
