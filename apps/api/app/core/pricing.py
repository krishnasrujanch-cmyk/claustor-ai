"""
Claustor AI — Pricing Configuration
Update prices here without touching endpoint logic.
All amounts in INR (not paise).
"""

PLAN_PRICING = {
    "starter": {
        "base_monthly":  7999,
        "addon_monthly": 1000,
        "label":         "Starter",
        "currency":      "INR",
    },
    "professional": {
        "base_monthly":  29999,
        "addon_monthly": 2500,
        "label":         "Professional",
        "currency":      "INR",
    },
}

BILLING_PERIODS = {
    "monthly":  {"charge_months": 1,  "free_months": 0, "label": "Monthly"},
    "6months":  {"charge_months": 5,  "free_months": 1, "label": "6 Months"},
    "12months": {"charge_months": 10, "free_months": 2, "label": "12 Months"},
}

GST_RATE = 0.18


def calculate_amount(plan: str, addon: bool, period: str) -> dict:
    """Calculate total amount for a plan+addon+period combination."""
    p = PLAN_PRICING.get(plan)
    if not p:
        raise ValueError(f"Unknown plan: {plan}")

    per = BILLING_PERIODS.get(period, BILLING_PERIODS["monthly"])
    months = per["charge_months"]

    base_amount  = p["base_monthly"] * months
    addon_amount = p["addon_monthly"] * months if addon else 0
    subtotal     = base_amount + addon_amount
    gst_amount   = round(subtotal * GST_RATE)
    total        = subtotal + gst_amount

    return {
        "base_amount":   base_amount,
        "addon_amount":  addon_amount,
        "gst_amount":    gst_amount,
        "total":         total,
        "total_paise":   total * 100,
        "period_months": months,
        "free_months":   per["free_months"],
        "currency":      p["currency"],
    }


def calculate_prorate_credit(
    current_plan: str,
    last_payment_amount: int,
    billing_period: str,
    next_billing_date,
) -> dict:
    """Calculate pro-rata credit for starter → professional upgrade."""
    from datetime import datetime, timezone

    if current_plan != "starter":
        return {"credit": 0, "daily_rate": 0, "remaining_days": 0}

    now = datetime.now(timezone.utc)
    if not next_billing_date or next_billing_date <= now:
        return {"credit": 0, "daily_rate": 0, "remaining_days": 0}

    period_info    = BILLING_PERIODS.get(billing_period, BILLING_PERIODS["monthly"])
    total_days     = (period_info["charge_months"] + period_info["free_months"]) * 30
    remaining_days = max(0, (next_billing_date - now).days)
    daily_rate     = last_payment_amount / total_days if total_days > 0 else 0
    credit         = round(daily_rate * remaining_days)

    return {
        "credit":         credit,
        "daily_rate":     round(daily_rate, 2),
        "remaining_days": remaining_days,
        "total_days":     total_days,
    }
