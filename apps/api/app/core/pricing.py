

def calculate_prorate_credit(
    current_plan: str,
    last_payment_amount: int,  # in INR (not paise)
    billing_period: str,
    next_billing_date,         # datetime
) -> dict:
    """
    Calculate pro-rata credit for starter → professional upgrade.
    Returns credit amount in INR.
    """
    from datetime import datetime, timezone

    if current_plan != "starter":
        return {"credit": 0, "daily_rate": 0, "remaining_days": 0}

    now = datetime.now(timezone.utc)
    if not next_billing_date or next_billing_date <= now:
        return {"credit": 0, "daily_rate": 0, "remaining_days": 0}

    period_info   = BILLING_PERIODS.get(billing_period, BILLING_PERIODS["monthly"])
    total_days    = (period_info["charge_months"] + period_info["free_months"]) * 30
    remaining_days = max(0, (next_billing_date - now).days)
    daily_rate    = last_payment_amount / total_days if total_days > 0 else 0
    credit        = round(daily_rate * remaining_days)

    return {
        "credit":         credit,
        "daily_rate":     round(daily_rate, 2),
        "remaining_days": remaining_days,
        "total_days":     total_days,
    }
