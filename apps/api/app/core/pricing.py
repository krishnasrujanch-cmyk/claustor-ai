"""
Claustor AI — Pricing Configuration
Update prices here without touching endpoint logic.
All amounts in INR (not paise).
"""

PLAN_PRICING = {
    "starter": {
        "base_monthly":  3999,   # ₹3,999/mo
        "addon_monthly": 1000,   # ₹1,000/mo for Industry Pack
        "label":         "Starter",
        "currency":      "INR",
    },
    "professional": {
        "base_monthly":  16499,  # ₹16,499/mo
        "addon_monthly": 2500,   # ₹2,500/mo for Industry Pack
        "label":         "Professional",
        "currency":      "INR",
    },
}

# Billing periods: months to charge (after free months)
BILLING_PERIODS = {
    "monthly":  {"charge_months": 1,  "free_months": 0, "label": "Monthly"},
    "6months":  {"charge_months": 5,  "free_months": 1, "label": "6 Months"},
    "12months": {"charge_months": 10, "free_months": 2, "label": "12 Months"},
}

GST_RATE = 0.18  # 18%

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
        "base_amount":    base_amount,
        "addon_amount":   addon_amount,
        "gst_amount":     gst_amount,
        "total":          total,
        "total_paise":    total * 100,  # for Razorpay
        "period_months":  months,
        "free_months":    per["free_months"],
        "currency":       p["currency"],
    }
