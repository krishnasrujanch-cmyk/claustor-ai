"""Australian Business Number (ABN) checksum validation."""

def validate(value: str) -> bool:
    """Validate ABN using standard checksum algorithm."""
    digits = [int(d) for d in value if d.isdigit()]
    if len(digits) != 11:
        return False
    try:
        weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
        digits[0] -= 1
        total = sum(w * d for w, d in zip(weights, digits))
        return total % 89 == 0
    except Exception:
        return False

def normalize(value: str) -> str:
    digits = ''.join(c for c in value if c.isdigit())
    return f"{digits[:2]} {digits[2:5]} {digits[5:8]} {digits[8:11]}"
